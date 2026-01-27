from datetime import datetime
import json
import uuid
import logging
import re
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow, WorkflowNode, WorkflowExecution, ExecutionStep, WorkflowEdge

# from services.ai_service import generate_response # Import for AI nodes

logger = logging.getLogger(__name__)

class WorkflowEngine:
    
    async def trigger_workflow(self, business_id: str, trigger_type: str, trigger_data: dict):
        """
        Finds active workflows matching the trigger and starts execution.
        """
        logger.info(f"[WorkflowEngine] Triggering {trigger_type} for Business {business_id} | Data: {trigger_data.keys()}")

        # 0. Orchestration Check: Active Suspension?
        # If the user is replying to a suspended workflow, RESUME it instead of starting new ones.
        if trigger_type == "message_created":
            resumed_id = await self.check_and_resume_execution(business_id, trigger_data)
            if resumed_id:
                logger.info(f"[WorkflowEngine] Resumed execution {resumed_id} instead of triggering new workflow.")
                return [resumed_id]

        async with AsyncSessionLocal() as session:
            # 1. Find Workflows
            # Allow 'keyword' trigger type to be matched by 'message_created' event
            target_types = [trigger_type]
            if trigger_type == "message_created":
                target_types.append("keyword")
                target_types.append("intent")
            elif trigger_type == "lead_status_update":
                target_types.append("lead_event")

            logger.info(f"[WorkflowEngine] Querying for BID: '{business_id}' | Types: {target_types}")
            stmt = select(Workflow).where(
                Workflow.business_id == business_id, 
                Workflow.is_active == True,
                Workflow.trigger_type.in_(target_types)
            )
            result = await session.execute(stmt)
            workflows = result.scalars().all()
            
            logger.info(f"[WorkflowEngine] Found {len(workflows)} active workflows. Data keywords: '{trigger_data.get('message') or trigger_data.get('message_body','')}'")
            for wf in workflows:
                logger.info(f"[WorkflowEngine] - WF: {wf.name} (Trigger: {wf.trigger_type}, Config: {wf.trigger_config})")
            
            executions = []
            for wf in workflows:
                # Check trigger config (e.g. keywords)
                logger.info(f"[WorkflowEngine] Checking WF {wf.id} ({wf.name}). Config: {wf.trigger_config}")
                if not self._check_trigger_match(wf.trigger_config, trigger_data):
                    logger.info(f"[WorkflowEngine] Workflow {wf.id} ({wf.name}) skipped: Trigger config mismatch.")
                    continue
                
                logger.info(f"[WorkflowEngine] Starting Workflow {wf.id} ({wf.name})")

                # Create Execution
                execution = WorkflowExecution(
                    workflow_id=wf.id,
                    business_id=business_id,
                    trigger_event=trigger_data,
                    context_data={"trigger": trigger_data, "business_id": business_id},
                    status="running"
                )
                session.add(execution)
                await session.flush() # Get ID
                
                # Find Start Node
                # Assuming Start Node has type 'start' or no incoming edges (simplified for now)
                start_node_stmt = select(WorkflowNode).where(
                    WorkflowNode.workflow_id == wf.id,
                    WorkflowNode.type == 'start'
                )
                start_node_res = await session.execute(start_node_stmt)
                start_node = start_node_res.scalar_one_or_none()
                
                if start_node:
                    # Dispatch Task
                    process_node_task.delay(execution.id, start_node.id)
                    executions.append(execution.id)
                else:
                    logger.warning(f"[WorkflowEngine] Workflow {wf.id} has no start node.")
                
            await session.commit()
            return executions

    async def check_and_resume_execution(self, business_id: str, trigger_data: dict):
        """
        Orchestration: Checks if this user has a suspended workflow and resumes it.
        Returns Execution ID if resumed, None otherwise.
        """
        # Support both WhatsApp (from_number) and Web (user_id)
        user_identifier = trigger_data.get("from_number") or trigger_data.get("user_id")
        
        if not user_identifier:
            logger.warning("[WorkflowEngine] Cannot check resume: No user_identifier in trigger data.")
            return None

        async with AsyncSessionLocal() as session:
            # Find suspended execution for this user (simple heuristic: look for from_number in trigger)
            # This relies on JSON containment or extracting the user ID. 
            # For now, let's assume we search where context_data->trigger->from_number matches.
            # This is slow without an index, but acceptable for MVP.
            
            # Using Python-side filtering for JSON safety across DBs,
            # but ideally we use JSON path query: execution.context_data['trigger']['from_number']
            
            # 1. Get all suspended executions for this business
            stmt = select(WorkflowExecution).where(
                WorkflowExecution.business_id == business_id,
                WorkflowExecution.status == 'suspended'
            )
            result = await session.execute(stmt)
            executions = result.scalars().all()
            
            target_execution = None
            for exc in executions:
                # Check if this execution belongs to this user
                # We assume context_data has "trigger"
                ex_trigger = exc.context_data.get("trigger", {})
                ex_user = ex_trigger.get("from_number") or ex_trigger.get("user_id")
                
                if ex_user == user_identifier:
                    target_execution = exc
                    break
            
            if not target_execution:
                return None
                
            # 2. Resume Logic
            logger.info(f"[WorkflowEngine] Resuming execution {target_execution.id} for user {user_identifier}")
            
            # Inject new message into context
            # We add it as "latest_reply" and also append to "history" if we had one
            # NORMALIZE: Ensure we have 'message_body'
            message_body = trigger_data.get("message_body") or trigger_data.get("message")
            
            resume_data = {
                "latest_reply": message_body,
                "latest_trigger": trigger_data
            }
            
            # Merge context
            target_execution.context_data = {**target_execution.context_data, **resume_data}
            target_execution.status = "running"
            
            # Retrieve resume point BEFORE clearing payload
            resume_node_id = None
            if hasattr(target_execution, 'resume_payload') and target_execution.resume_payload:
                 resume_node_id = target_execution.resume_payload.get('node_id')
            
            target_execution.resume_payload = None # Clear suspension
            
            session.add(target_execution)
            await session.commit()
            
            # 3. Trigger Next Step
            if not resume_node_id:
                logger.error(f"[WorkflowEngine] Cannot resume execution {target_execution.id}: missing resume_node_id")
                return None
                
            node = await session.get(WorkflowNode, resume_node_id)
            if node:
                # We pretend the Wait Node just finished and produced this output
                node_output = {"user_reply": message_body}
                
                # Update the STEP that was suspended? 
                # Ideally we mark the suspended step as completed now.
                # But for now, we just proceed to next nodes.
                
                next_nodes = await get_next_nodes(session, node, node_output)
                if not next_nodes:
                     logger.info(f"[WorkflowEngine] Resumed node {node.id} has no outgoing edges.")
                
                for next_node in next_nodes:
                     process_node_task.delay(target_execution.id, next_node.id)
                     logger.info(f"[WorkflowEngine] Dispatched next node {next_node.id}")
            
            return target_execution.id

    async def create_workflow(self, business_id: str, workflow_data: dict):
        """
        Parses a full workflow DAG and saves it to the database.
        Request Body: {
            "name": "...", 
            "trigger_type": "...",
            "trigger_config": {}, 
            "nodes": [...], 
            "edges": [...]
        }
        """
        async with AsyncSessionLocal() as session:
            try:
                # 1. Create Workflow
                wf = Workflow(
                    business_id=business_id,
                    name=workflow_data.get("name", "Untitled Workflow"),
                    description=workflow_data.get("description"),
                    trigger_type=workflow_data.get("trigger_type"),
                    trigger_config=workflow_data.get("trigger_config", {}),
                    definition=workflow_data.get("definition", {}), # Save UI State
                    is_active=True
                )
                session.add(wf)
                await session.flush() # Get ID
                
                # 2. Map Frontend IDs to DB IDs (if needed, or just use provided if UUID)
                # For simplicity, we assume frontend provides UUIDs or we generate them.
                # But to maintain Referential Integrity, we must ensure consistency.
                # Let's assume nodes come with 'id' that we respect if possible, or we might break edges.
                # Simplest: Save nodes with provided IDs (must be unique strings).
                
                node_map = {} # client_id -> db_obj
                
                nodes_data = workflow_data.get("nodes", [])
                for n_data in nodes_data:
                    node = WorkflowNode(
                        id=n_data.get("id", str(uuid.uuid4())),
                        workflow_id=wf.id,
                        type=n_data.get("type"),
                        label=n_data.get("label"),
                        config=n_data.get("config", {}),
                        platform_meta=n_data.get("position") or n_data.get("platform_meta") or {}
                    )
                    session.add(node)
                    node_map[node.id] = node
                
                # 3. Create Edges
                edges_data = workflow_data.get("edges", [])
                for e_data in edges_data:
                    source_id = e_data.get("source") or e_data.get("source_id")
                    target_id = e_data.get("target") or e_data.get("target_id")
                    
                    if source_id not in node_map or target_id not in node_map:
                        logger.warning(f"Edge references missing node: {source_id} -> {target_id}")
                        continue
                        
                    edge = WorkflowEdge(
                        workflow_id=wf.id,
                        source_id=source_id,
                        target_id=target_id,
                        condition_value=e_data.get("condition") or e_data.get("condition_value")
                    )
                    session.add(edge)
                
                await session.commit()
                return {"status": "success", "id": wf.id}
                
            except Exception as e:
                logger.error(f"Error creating workflow: {e}")
                await session.rollback()
                return {"status": "error", "message": str(e)}

    async def get_workflows(self, business_id: str):
        """
        List all workflows for a business.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Workflow).where(Workflow.business_id == business_id)
            result = await session.execute(stmt)
            workflows = result.scalars().all()
            return workflows

    async def delete_workflow(self, business_id: str, workflow_id: str):
        """
        Delete a workflow by ID.
        """
        async with AsyncSessionLocal() as session:
            try:
                wf = await session.get(Workflow, workflow_id)
                if not wf or wf.business_id != business_id:
                     return False
                
                await session.delete(wf)
                await session.commit()
                return True
            except Exception as e:
                logger.error(f"Error deleting workflow {workflow_id}: {e}")
                await session.rollback()
                return False

    async def get_executions(self, business_id: str, workflow_id: str = None, limit: int = 50):
        """
        List past executions.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(WorkflowExecution).where(WorkflowExecution.business_id == business_id)
            if workflow_id:
                stmt = stmt.where(WorkflowExecution.workflow_id == workflow_id)
            
            stmt = stmt.order_by(WorkflowExecution.started_at.desc()).limit(limit)
            result = await session.execute(stmt)
            executions = result.scalars().all()
            return executions

    async def trigger_specific_workflow(self, business_id: str, workflow_id: str, trigger_data: dict):
        """
        Manually trigger a specific workflow by ID.
        """
        async with AsyncSessionLocal() as session:
            wf = await session.get(Workflow, workflow_id)
            if not wf or wf.business_id != business_id:
                 return None
            
            execution = WorkflowExecution(
                    workflow_id=wf.id,
                    business_id=business_id,
                    trigger_event=trigger_data,
                    context_data={"trigger": trigger_data},
                    status="running"
                )
            session.add(execution)
            await session.flush()
            
            # Find Start Node
            start_node_stmt = select(WorkflowNode).where(
                WorkflowNode.workflow_id == wf.id,
                WorkflowNode.type == 'start'
            )
            start_node_res = await session.execute(start_node_stmt)
            start_node = start_node_res.scalar_one_or_none()
            
            if start_node:
                process_node_task.delay(execution.id, start_node.id)
                await session.commit()
                return execution.id
            else:
                await session.rollback()
                return None

    def _check_trigger_match(self, config: dict, data: dict) -> bool:
        """Evaluate if the trigger data matches the config"""
        if not config: return True
        
        # Keyword Match
        if "keyword" in config:
            message = data.get("message", "").lower()
            keyword = config["keyword"].lower()
            if keyword not in message:
                return False
        
        # Intent Match
        if "intent" in config:
            intent = data.get("intent")
            if intent != config["intent"]:
                return False
        
        # Lead Status Match (for lead_event triggers)
        if "status" in config:
            new_status = data.get("new_status", "").lower()
            target_status = config["status"].lower()
            if new_status != target_status:
                return False
                
        return True

workflow_engine = WorkflowEngine()

from celery import shared_task

# --- Celery Tasks ---

@shared_task(name="process_node")
def process_node_task(execution_id: str, node_id: str):
    """
    Celery task wrapper to run async node processing synchronously
    """
    import asyncio
    asyncio.run(process_node_async(execution_id, node_id))

async def process_node_async(execution_id: str, node_id: str):
    async with AsyncSessionLocal() as session:
        try:
            node = await session.get(WorkflowNode, node_id)
            execution = await session.get(WorkflowExecution, execution_id)
            
            if not node or not execution:
                return
            
            # 1. Create Step Record
            step = ExecutionStep(
                execution_id=execution.id,
                node_id=node.id,
                status="running",
                input_data=execution.context_data # simplified
            )
            session.add(step)
            await session.commit()
            
            # 2. Execute Logic
            output = await execute_node_logic(node, execution.context_data)
            
            # Orchestration Check: Did the node ask to suspend?
            if isinstance(output, dict) and output.get("orchestration_signal") == "suspend":
                step.status = "suspended"
                step.completed_at = datetime.utcnow()
                
                execution.status = "suspended"
                execution.resume_payload = {
                    "node_id": output.get("resume_node_id"), 
                    "step_id": step.id
                }
                
                logger.info(f"Execution {execution.id} suspended at node {node.id}")
                session.add(execution)
                session.add(step)
                await session.commit()
                return # STOP HERE

            # 3. Update Step & Context
            step.output_data = output
            step.status = "completed"
            step.completed_at = datetime.utcnow()
            
            # Update Global Context (Merge)
            if isinstance(output, dict):
                execution.context_data = {**execution.context_data, **output}
                session.add(execution) # Mark for update
            
            await session.commit()
            
            # 4. Determine Next Nodes
            next_nodes = await get_next_nodes(session, node, output)
            
            # Check for delay signal
            delay_seconds = 0
            if isinstance(output, dict) and output.get("orchestration_signal") == "delay":
                delay_seconds = output.get("seconds", 0)
            
            # 5. Dispatch Next
            for next_node in next_nodes:
                if delay_seconds > 0:
                     eta = datetime.utcnow().timestamp() + delay_seconds
                     # Celery countdown or eta
                     process_node_task.apply_async(args=[execution.id, next_node.id], countdown=delay_seconds)
                     logger.info(f"Scheduled next node {next_node.id} with delay {delay_seconds}s")
                else:
                     process_node_task.delay(execution.id, next_node.id)
                 
            # If no next nodes, checking if end of workflow?
            if not next_nodes:
                # If we delayed, we are technically still "running" until the next one picks up?
                # Actually if next_nodes is empty, delay doesn't matter (nothing to delay).
                
                # Check if all branches done? simplified: just mark completed
                execution.status = "completed"
                execution.completed_at = datetime.utcnow()
                session.add(execution)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error processing node {node_id}: {e}")
            # Mark step failed
            # step.status = "failed"
            # step.error = str(e)
            # await session.commit()

def get_context_value(context: dict, key: str):
    """
    Resolves a variable from context. 
    Supports nested keys (e.g. 'trigger.message_body') and flat keys.
    """
    if not key: return None
    
    parts = key.split('.')
    val = context
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            val = None
            break
            
    # Fallback: if not found by path, check if it exists as a flat key in the root
    if val is None and len(parts) == 1:
        val = context.get(key)
        
    # Extra fallback: check inside 'trigger' if not found at root
    if val is None and len(parts) == 1:
        val = context.get("trigger", {}).get(key)
        
    return val

def hydrate_text(text: str, context: dict):
    """
    Replaces {{variable}} placeholders in text with values from context.
    """
    if not isinstance(text, str): return text
    
    def replace_var(match):
        key = match.group(1).strip()
        val = get_context_value(context, key)
        return str(val) if val is not None else match.group(0)
        
    return re.sub(r'\{\{(.*?)\}\}', replace_var, text)

async def execute_node_logic(node: WorkflowNode, context: dict):
    """
    Actual business logic for a node
    """
    node_type = node.type
    config = node.config or {}
    
    if node_type == "start":
        return {"status": "started"}
        
    elif node_type == "action":
        action_type = config.get("action_type", "send_message")
        
        if action_type == "send_message":
            # Action: Send WhatsApp Message
            from services.whatsapp_service import send_whatsapp_message
            
            target_number = context.get("trigger", {}).get("from_number") or config.get("to_number")
            message_template = config.get("template", "Hello from InteractAI!")
            
            # Simple template substitution
            message_body = hydrate_text(message_template, context)
            
            if target_number:
                await send_whatsapp_message(target_number, message_body)
                return {"action_result": "sent", "message_body": message_body}
            
            # Fallback: Web Chat or Unknown Platform
            elif context.get("trigger", {}).get("user_id"):
                 from services.db_service import store_message
                 user_id = context.get("trigger", {}).get("user_id")
                 business_id = context.get("business_id", "default")
                 
                 await store_message(business_id, user_id, message_body, "agent", platform="web")
                 return {"action_result": "sent_web", "message_body": message_body}

            else:
                return {"action_result": "failed", "error": "No target number or user_id found"}

        elif action_type == "create_ticket":
            # Action: Create Support Ticket / Booking
            from services.db_service import create_ticket
            
            ticket_data = {
                "subject": config.get("subject", "New Workflow Ticket"),
                "description": config.get("description", "Created via Automation"),
                "status": "open",
                "priority": config.get("priority", "medium")
            }
            # Add context info to description
            ticket_data["description"] += f"\nContext: {json.dumps(context.get('trigger', {}), default=str)}"
            
            ticket_id = await create_ticket(context.get("business_id", "default"), ticket_data)
            return {"ticket_id": ticket_id, "action_result": "ticket_created"}

        elif action_type == "assign_agent":
            # Action: Assign to Agent
            from services.db_service import assign_agent
            
            agent_id = config.get("agent_id")
            target_id = context.get("ticket_id") # If we just created one
            
            if target_id and agent_id:
                await assign_agent(context.get("business_id", "default"), target_id, agent_id, "ticket")
                return {"assigned_to": agent_id, "action_result": "assigned"}
            else:
                return {"action_result": "skipped", "reason": "missing_id"}
        
        return {"action_result": "unknown_type"}

    elif node_type == "ai_inference":
        # AI: Generate Text via Advanced Prompting
        from services.ai_service import generate_response
        from services.prompt_service import prompt_service
        from services.db_service import get_business_profile, get_knowledge_documents
        
        business_id = context.get("business_id", "default")
        
        # 1. Fetch Business Context
        profile = await get_business_profile(business_id)
        knowledge_docs = await get_knowledge_documents(business_id)
        
        # Inject docs into profile for the prompt builder
        if knowledge_docs:
            profile['knowledge_docs'] = knowledge_docs
            
        # 2. Build Base System Persona (Industry, Tone, Rules)
        system_persona = prompt_service.build_system_prompt(profile)
        
        # 3. Add Node-Specific Goal
        node_goal = config.get("prompt_template", "You are a helpful assistant.")
        
        # 4. Add Workflow Execution Context
        # Flatten trigger data for the AI to see
        trigger_context = context.get("trigger", {})
        trigger_summary = f"User Input: {trigger_context.get('message_body', '')}\nFrom: {trigger_context.get('from_number', 'Unknown')}"
        
        # Construct the final "Mega-Prompt"
        full_system_instruction = f"""
{system_persona}

*** WORKFLOW GOAL ***
Your current specific objective in this workflow is:
{node_goal}

*** CONTEXT ***
{trigger_summary}
Current Workflow State: {json.dumps(context, default=str)}

Respond directly to the user to achieve the WORKFLOW GOAL.
"""
        
        user_message = config.get("input_text") or trigger_context.get("message_body") or "Continue"
        
        # Call AI Service
        response_text = await generate_response(
            user_message=user_message,
            system_instruction=full_system_instruction,
            business_id=business_id
        )
        
        # AUTO-SEND: If configured to send directly or if it's the primary response node
        if config.get("auto_send", True):
            from services.whatsapp_service import send_whatsapp_message
            target_number = context.get("trigger", {}).get("from_number")
            
            if target_number:
                await send_whatsapp_message(target_number, response_text)
                logger.info(f"[WorkflowEngine] AI Agent auto-sent response to {target_number}")
            elif context.get("trigger", {}).get("user_id"):
                from services.db_service import store_message
                user_id = context.get("trigger", {}).get("user_id")
                await store_message(business_id, user_id, response_text, "agent", platform="web")
                logger.info(f"[WorkflowEngine] AI Agent auto-stored response for web user {user_id}")
        
        return {"ai_output": response_text}
        
    elif node_type == "ai_extract":
        # Intelligence: Structured Data Extraction
        from services.ai_service import generate_response
        
        target_fields = config.get("fields", []) # e.g. [{"name": "email", "type": "email"}]
        schema_desc = json.dumps(target_fields)
        
        # Context to analyze (usually the latest reply or full history)
        trigger_context = context.get("trigger", {})
        # Try to gather history from context
        history = context.get("history", []) # If we store history in context
        history_text = "\n".join([f"{h.get('role')}: {h.get('content')}" for h in history[-10:]])
        
        text_to_analyze = f"""
        Latest Message: {trigger_context.get('message_body', '') or trigger_context.get('message', '')}
        
        Chat History:
        {history_text}
        
        Previous AI Output: {context.get('ai_output', '')}
        """
        
        # Prepare schema description for prompt
        fields_str = ""
        for f in target_fields:
            fields_str += f"- {f.get('name')}: {f.get('description', 'The ' + f.get('name'))} (Type: {f.get('type','string')})\n"

        system_instruction = f"""
        You are an elite Data Extraction Specialist. 
        Your task is to extract specific attributes from the provided chat snippet and return a RAW JSON object.

        FIELDS TO EXTRACT:
        {fields_str}

        CRITICAL RULES:
        1. return ONLY valid JSON.
        2. No markdown blocks. No conversational text.
        3. If you can't find a value, set it to null.
        4. Be precise. If the user says 'I am from Apple', company is 'Apple'.
        5. For numbers (budget, etc.), return only the numeric value (no $ or commas).

        EXAMPLE RESPONSE:
        {{ "company": "Tesla", "budget": 50000 }}
        """
        
        response_text = await generate_response(
            user_message=text_to_analyze,
            system_instruction=system_instruction,
            business_id=context.get("business_id", "default")
        )
        
        # Parse JSON
        try:
            # Cleanup potential markdown
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            extracted_data = json.loads(cleaned_text)
            
            # Return merged into a key? Or top level?
            # Let's return as top level to allow quick access in conditions
            return extracted_data
        except:
            logger.error(f"Failed to parse AI Extract JSON: {response_text}")
            return {"extraction_error": "failed_to_parse_json"}
    
    elif node_type == "time_delay":
        # Intelligence: Temporal Logic
        # Returns a signal to the dispatcher to delay the NEXT step
        seconds = int(config.get("seconds", 0))
        return {"orchestration_signal": "delay", "seconds": seconds}

    elif node_type == "http_request":
        # Intelligence: External Connectivity
        import httpx
        
        url = config.get("url")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        
        # Hydrate variables in URL/Body (simple replacement)
        def hydrate(text):
            if not isinstance(text, str): return text
            def replace_var(match):
                key = match.group(1).strip()
                val = get_context_value(context, key)
                return str(val) if val is not None else match.group(0)
            return re.sub(r'\{\{(.*?)\}\}', replace_var, text)
        
        url = hydrate_text(url, context)
        if isinstance(body, dict):
            body_str = hydrate_text(json.dumps(body), context)
            body = json.loads(body_str)
        elif isinstance(body, str):
            body = hydrate_text(body, context)

        if not url:
            return {"error": "Missing URL"}
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=headers, json=body, timeout=10.0)
                # We don't raise error immediately, we let the workflow handle the status code
                
                return {
                    "status_code": response.status_code,
                    "response_body": response.json() if response.headers.get("content-type") == "application/json" else response.text
                }
            except Exception as e:
                return {"error": str(e)}

    elif node_type == "lead_capture":
        # CRM: Save Lead
        from services.db_service import save_lead
        
        # Hydrate variables for name/notes
        name_val = hydrate_text(config.get("name", "{{customer_name}}"), context)
        if name_val == "{{customer_name}}": name_val = context.get("customer_name") or "Unknown"
        
        notes_val = hydrate_text(config.get("notes", "Captured via Workflow {{workflow_id}}"), context)
        if "{{workflow_id}}" in notes_val: notes_val = notes_val.replace("{{workflow_id}}", str(node.workflow_id))

        trigger = context.get("trigger", {})
        contact_info = trigger.get("from_number") or trigger.get("user_id")
        
        # Merge AI extracted data if available
        ai_data = {}
        if isinstance(context.get("ai_output"), dict):
            ai_data = context.get("ai_output")
        elif isinstance(context.get("extracted_data"), dict): # Support explicit key if we add it
            ai_data = context.get("extracted_data")

        lead_data = {
            "name": name_val,
            "contact": contact_info,
            "email": ai_data.get("email") or (contact_info if "@" in (contact_info or "") else None),
            "phone": ai_data.get("phone") or (contact_info if "@" not in (contact_info or "") else None),
            "source": "workflow_automation",
            "notes": notes_val,
            "status": config.get("status", "new"),
            "tags": ai_data.get("tags", []),
            "value": ai_data.get("budget") or ai_data.get("value"),
            "custom_fields": ai_data,
            "conversation_id": trigger.get("user_id"),
            "last_interaction_at": datetime.utcnow()
        }
        
        lead_id = await save_lead(context.get("business_id", "default"), lead_data)
        return {"lead_id": lead_id, "lead_status": "captured"}

    elif node_type == "wait_for_reply":
        # Orchestration: Suspend Execution
        return {"orchestration_signal": "suspend", "resume_node_id": node.id}

    elif node_type == "appointment_booking":
        # Scheduling: Native Appointment Flow
        from services.scheduling_service import scheduling_service
        from services.ai_service import generate_response
        
        business_id = context.get("business_id", "default")
        
        # Check if we are RESUMING or STARTING
        latest_reply = context.get("latest_reply")
        pending_slots = context.get("pending_slots")
        
        if latest_reply and pending_slots:
            # --- RESUME LOGIC: Confirm Slot ---
            logger.info(f"[WorkflowEngine] Resuming Appointment Booking for BID {business_id}. Reply: {latest_reply}")
            
            # Use AI to match the reply to one of the slots
            match_prompt = f"""
            Identify which of these slots the user selected. 
            SLOTS: {json.dumps(pending_slots)}
            USER REPLY: "{latest_reply}"
            
            Return ONLY the index (0, 1, 2...) of the slot, or "none" if no match.
            """
            match_idx_str = await generate_response(match_prompt, system_instruction="You are a precise slot matcher. Return ONLY the index or 'none'.", business_id=business_id)
            
            try:
                idx = int(re.sub(r'[^\d]', '', match_idx_str))
                selected_slot = pending_slots[idx]
                
                # Book it!
                lead_id = context.get("lead_id") # If we captured lead before
                conversation_id = context.get("trigger", {}).get("user_id")
                apt_type_id = config.get("appointment_type_id")
                
                res = await scheduling_service.book_appointment(
                    business_id=business_id,
                    appointment_type_id=apt_type_id,
                    start_at=datetime.fromisoformat(selected_slot["start"]),
                    lead_id=lead_id,
                    conversation_id=conversation_id,
                    notes=f"Booked via Workflow: {node.workflow_id}"
                )
                
                if res["success"]:
                    confirmation_msg = f"Confirmed! You are booked for {selected_slot['display']}."
                    # Send confirmation
                    target_number = context.get("trigger", {}).get("from_number")
                    if target_number:
                        from services.whatsapp_service import send_whatsapp_message
                        await send_whatsapp_message(target_number, confirmation_msg)
                    else:
                        from services.db_service import store_message
                        await store_message(business_id, conversation_id, confirmation_msg, "agent", platform="web")
                    
                    return {"booking_result": "success", "appointment_id": res["appointment_id"], "booked_slot": selected_slot}
                else:
                    return {"booking_result": "failed", "error": res.get("error")}
            except:
                # No match? Ask again or fail.
                retry_msg = "I'm sorry, I didn't quite catch that. Which of those times works best for you?"
                return {"orchestration_signal": "suspend", "resume_node_id": node.id, "pending_slots": pending_slots, "ai_output": retry_msg}

        else:
            # --- START LOGIC: Propose Slots ---
            apt_type_id = config.get("appointment_type_id")
            if not apt_type_id:
                # Fallback: get first available type
                from database.models.scheduling import AppointmentType
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(AppointmentType).where(AppointmentType.business_id == business_id).limit(1))
                    apt_type = res.scalar_one_or_none()
                    apt_type_id = apt_type.id if apt_type else None
            
            if not apt_type_id:
                return {"error": "No appointment types found"}

            # Get slots for next 3 days
            all_slots = []
            for i in range(3):
                target_date = (datetime.utcnow() + timedelta(days=i+1)).date()
                slots = await scheduling_service.get_available_slots(business_id, target_date, apt_type_id)
                all_slots.extend(slots)
            
            # Pick top 3
            proposed_slots = []
            for s in all_slots[:3]:
                proposed_slots.append({
                    "start": s.isoformat(),
                    "display": s.strftime("%A, %b %d at %I:%M %p")
                })
            
            if not proposed_slots:
                return {"booking_result": "no_slots", "ai_output": "I'm sorry, we don't have any available slots right now."}

            # Propose via AI
            slots_text = "\n".join([f"- {s['display']}" for s in proposed_slots])
            proposal_prompt = f"Invite the user to book an appointment. Offer these slots and ask them to pick one:\n{slots_text}"
            
            proposal_msg = await generate_response(proposal_prompt, business_id=business_id)
            
            # Send proposal
            target_number = context.get("trigger", {}).get("from_number")
            conversation_id = context.get("trigger", {}).get("user_id")
            if target_number:
                from services.whatsapp_service import send_whatsapp_message
                await send_whatsapp_message(target_number, proposal_msg)
            else:
                from services.db_service import store_message
                await store_message(business_id, conversation_id, proposal_msg, "agent", platform="web")

            return {
                "orchestration_signal": "suspend", 
                "resume_node_id": node.id, 
                "pending_slots": proposed_slots, 
                "ai_output": proposal_msg
            }

    elif node_type == "condition":
        # Condition: Evaluate Logic
        # Returns a value that Edges will match against
        variable = config.get("variable") # e.g. "ai_output" or "trigger.message_body"
        operator = config.get("operator", "contains") # equals, contains, greater_than, exists
        target_value = config.get("value")
        
        actual_value = get_context_value(context, variable)
        
        # Simple evaluation logic
        result = "false"
        
        if operator == "exists":
            if actual_value is not None and actual_value != "":
                result = "true"
                
        elif actual_value is None:
             result = "false" # Cannot compare None
             
        elif operator == "equals":
            if str(actual_value).lower() == str(target_value).lower():
                result = "true"
                
        elif operator == "contains":
            if target_value and str(target_value).lower() in str(actual_value).lower():
                result = "true"
                
        elif operator == "greater_than":
            try:
                # Clean numeric strings (remove $, commas, etc)
                def clean_num(v):
                    if isinstance(v, (int, float)): return float(v)
                    cleaned = re.sub(r'[^\d.]', '', str(v))
                    return float(cleaned) if cleaned else 0.0

                if clean_num(actual_value) > clean_num(target_value):
                    result = "true"
            except (ValueError, TypeError):
                # Fallback to string comparison? Or just fail false.
                if str(actual_value) > str(target_value):
                    result = "true"
        
        # Return the evaluated result as "condition_eval"
        return {"condition_eval": result}
        
    return {}

async def get_next_nodes(session, current_node, output):
    """
    Finds outgoing edges and checks conditions
    """
    stmt = select(WorkflowEdge).where(WorkflowEdge.source_id == current_node.id)
    result = await session.execute(stmt)
    edges = result.scalars().all()
    
    next_nodes = []
    
    for edge in edges:
        # Check condition
        if edge.condition_value:
            # If edge has a condition, check against output "condition_eval"
            eval_result = output.get("condition_eval")
            # Simple string match
            if str(eval_result) != edge.condition_value:
                continue
        
        # Load Target Node
        target = await session.get(WorkflowNode, edge.target_id)
        if target:
            next_nodes.append(target)
            
    return next_nodes
