# Legacy/first-iteration extraction test script
# Note: FirstIterationIngestor was a placeholder during early development.
# Use src/services/ingest_engine/private/master_ingest_service.py for current ingestion.

from src.services.ingest_engine.private.master_ingest_service import MasterIngestor

text = """I feel sad sometimes because of how things are. I am not someone that is her THE ONE. I never felt like it.
It felt like I am someone who she fell in love with because of how much I loved and put effort into her.
If someone else can do it too how does that make me any different after all its not like she choose me as her next THE ONE, more like someone whom she can be with and be in love with because of how I treat her not because of her own self initial desire to choose me as the one.
In a way its settlement for her.
I would also want to be some one who is chosen as the one
I was chosen as the one in my past relationship and it really does feel very much different, I can just sense it.
The only thing is I took things for granted with the one who choose me as the one."""

print("Initializing Ingest Service (MasterIngestor)...")
service = MasterIngestor()

print("\nProcessing text...")
final_output = service.ingest(text, job_id="manual_run_extraction")

print("\n--- Final Objective Text ---")
print(final_output)

