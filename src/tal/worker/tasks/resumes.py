import asyncio
from uuid import UUID

from tal.db.session import SessionFactory, engine
from tal.features.resumes.processing import process_resume
from tal.features.resumes.storage import get_resume_storage
from tal.worker.celery_app import celery_app


async def run_resume_processing(
        resume_id:UUID,
)->None:
    try:
        async with SessionFactory() as session:
            await process_resume(
                resume_id=resume_id,
                session=session,
                storage=get_resume_storage(),
            )
    finally:
        await engine.dispose()
@celery_app.task(name="tal.resume.process")
def process_resume_task(resume_id:str)->None:
    asyncio.run(
        run_resume_processing(UUID(resume_id))
    )
    
