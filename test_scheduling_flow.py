import asyncio
import json
from datetime import datetime
from services.workflow_engine import workflow_engine
from services.scheduling_service import scheduling_service
from database.session import AsyncSessionLocal
from database.models.scheduling import AppointmentType, AvailabilityRule
from database.models.workflow import Workflow, WorkflowNode, WorkflowEdge
from services.db_service import resolve_business_id

async def test_scheduling_flow():
    business_id = "test_biz_123"
    bid = await resolve_business_id(business_id)
    
    async with AsyncSessionLocal() as session:
        # 1. Setup Data
        # Appointment Type
        apt_type = AppointmentType(business_id=bid, name="Test Consultation", duration_minutes=30)
        session.add(apt_type)
        await session.flush()
        
        # Availability
        for i in range(5):
            from datetime import time
            rule = AvailabilityRule(business_id=bid, day_of_week=i, start_time=time(9, 0), end_time=time(17, 0))
            session.add(rule)
        
        # 2. Setup Workflow
        workflow = Workflow(id="test_wf", business_id=bid, name="Scheduling Test")
        node = WorkflowNode(
            id="node_book",
            workflow_id="test_wf",
            type="appointment_booking",
            config={"appointment_type_id": apt_type.id}
        )
        session.add(workflow)
        session.add(node)
        await session.commit()
        
        print(f"\n--- STEP 1: INITIAL TRIGGER ---")
        # 3. Execute Workflow (Initial)
        result = await workflow_engine.execute_node_logic(node, {"business_id": bid, "trigger": {"user_id": "user_1"}})
        
        print(f"Signal: {result.get('orchestration_signal')}")
        print(f"Proposed Slots: {len(result.get('pending_slots', []))}")
        print(f"AI Message: {result.get('ai_output')[:50]}...")
        
        if result.get("orchestration_signal") == "suspend":
            print(f"\n--- STEP 2: RESUME TRIGGER (Fuzzy Match) ---")
            # 4. Resume Execution
            # Simulate user picking the first slot
            selected_slot = result["pending_slots"][0]
            print(f"User picks: {selected_slot['display']}")
            
            # Context for resume
            context = {
                "business_id": bid,
                "latest_reply": "Let's go with the first one, " + selected_slot['display'],
                "pending_slots": result["pending_slots"],
                "trigger": {"user_id": "user_1"}
            }
            
            resume_result = await workflow_engine.execute_node_logic(node, context)
            
            print(f"Booking Status: {resume_result.get('booking_result')}")
            if resume_result.get("booking_result") == "success":
                print(f"Appointment ID: {resume_result.get('appointment_id')}")
                
                # Verify in DB
                from database.models.scheduling import Appointment
                from sqlalchemy import select
                apt_check = await session.execute(select(Appointment).where(Appointment.id == resume_result["appointment_id"]))
                apt = apt_check.scalar_one_or_none()
                if apt:
                    print(f"SUCCESS: Appointment found in DB for {apt.start_at}")
                else:
                    print("ERROR: Appointment NOT found in DB")
            else:
                print(f"ERROR: Booking failed: {resume_result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_scheduling_flow())
