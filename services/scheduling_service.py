import logging
from datetime import datetime, timedelta, time as py_time
from sqlalchemy import select, and_
from database.session import AsyncSessionLocal
from database.models.scheduling import Appointment, AppointmentType, AvailabilityRule
from database.models.crm import Lead
import uuid

logger = logging.getLogger(__name__)

class SchedulingService:
    async def get_available_slots(self, business_id: str, date: datetime.date, appointment_type_id: str):
        """
        Calculates available slots for a specific date and appointment type.
        """
        async with AsyncSessionLocal() as session:
            # 1. Get Appointment Type Info
            apt_type = await session.get(AppointmentType, appointment_type_id)
            if not apt_type or apt_type.business_id != business_id:
                logger.error(f"Appointment type {appointment_type_id} not found for business {business_id}")
                return []
            
            duration = apt_type.duration_minutes
            
            # 2. Get Availability Rules for the day of week
            day_of_week = date.weekday() # 0 = Monday
            rule_stmt = select(AvailabilityRule).where(
                AvailabilityRule.business_id == business_id,
                AvailabilityRule.day_of_week == day_of_week,
                AvailabilityRule.is_active == True
            )
            rule_res = await session.execute(rule_stmt)
            rules = rule_res.scalars().all()
            
            if not rules:
                return [] # No availability defined for this day
            
            # 3. Get existing appointments for the day
            start_of_day = datetime.combine(date, py_time.min)
            end_of_day = datetime.combine(date, py_time.max)
            
            apt_stmt = select(Appointment).where(
                Appointment.business_id == business_id,
                Appointment.start_at >= start_of_day,
                Appointment.start_at <= end_of_day,
                Appointment.status.in_(["scheduled", "confirmed"])
            )
            apt_res = await session.execute(apt_stmt)
            existing_apts = apt_res.scalars().all()
            
            # 4. Generate Slots
            available_slots = []
            for rule in rules:
                current_time = datetime.combine(date, rule.start_time)
                end_time = datetime.combine(date, rule.end_time)
                
                while current_time + timedelta(minutes=duration) <= end_time:
                    slot_start = current_time
                    slot_end = current_time + timedelta(minutes=duration)
                    
                    # Check for overlap
                    overlap = False
                    for apt in existing_apts:
                        if (slot_start < apt.end_at) and (apt.start_at < slot_end):
                            overlap = True
                            break
                    
                    if not overlap:
                        # Don't show past slots for today
                        if slot_start > datetime.utcnow():
                            available_slots.append(slot_start)
                    
                    current_time += timedelta(minutes=duration)
                    
            return available_slots

    async def book_appointment(self, business_id: str, appointment_type_id: str, start_at: datetime, lead_id: int = None, conversation_id: str = None, notes: str = None):
        """
        Records a new appointment.
        """
        async with AsyncSessionLocal() as session:
            # 1. Get Type
            apt_type = await session.get(AppointmentType, appointment_type_id)
            if not apt_type:
                return {"success": False, "error": "Invalid appointment type"}
            
            end_at = start_at + timedelta(minutes=apt_type.duration_minutes)
            
            # 2. Re-check availability (concurrency safety)
            # (In a high-traffic app, we should use a lock or transaction isolation)
            
            # 3. Create Appointment
            apt = Appointment(
                business_id=business_id,
                lead_id=lead_id,
                conversation_id=conversation_id,
                appointment_type_id=appointment_type_id,
                start_at=start_at,
                end_at=end_at,
                notes=notes,
                status="scheduled"
            )
            session.add(apt)
            
            # 4. Log Activity if Lead exists
            if lead_id:
                from database.models.crm import LeadActivity
                activity = LeadActivity(
                    lead_id=lead_id,
                    business_id=business_id,
                    type="appointment_booked",
                    content={
                        "appointment_id": apt.id,
                        "type": apt_type.name,
                        "start_at": start_at.isoformat()
                    },
                    created_by="system"
                )
                session.add(activity)
            
            await session.commit()
            return {"success": True, "appointment_id": apt.id}

    async def get_business_appointments(self, business_id: str, start_date: datetime = None, end_date: datetime = None, lead_id: int = None):
        async with AsyncSessionLocal() as session:
            stmt = select(Appointment).where(Appointment.business_id == business_id)
            if lead_id:
                stmt = stmt.where(Appointment.lead_id == lead_id)
            if start_date:
                stmt = stmt.where(Appointment.start_at >= start_date)
            if end_date:
                stmt = stmt.where(Appointment.start_at <= end_date)
            
            stmt = stmt.order_by(Appointment.start_at.asc())
            res = await session.execute(stmt)
            return res.scalars().all()

scheduling_service = SchedulingService()
