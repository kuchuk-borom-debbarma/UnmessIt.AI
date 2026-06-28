import os
import random
from datetime import datetime, timedelta

# The key story points that test multi-hop RAG reasoning
# We will inject these at specific dates.
KEY_EVENTS = {
    "2021-01-12": "[Jan 12, 2021 - Globex Internal Memo]\nWelcome to the team, Alex! As the newly appointed Lead for Project Alpha, you will be spearheading our cloud migration strategy. We are excited to have you in our New York headquarters. Project Alpha is our biggest bet this year.",
    
    "2021-03-05": "[March 5, 2021 - Meeting Transcript]\nAlex: \"The cloud migration is going well. We are evaluating several vendors. I'm loving the NY office, by the way, the pizza here is great.\"\nSam: \"Glad to hear it. Let's keep the focus on the Q2 deliverables.\"",
    
    "2022-11-18": "[Nov 18, 2022 - Press Release]\nGlobex is thrilled to announce the acquisition of Initech. This synergistic merger will allow us to absorb Initech's machine learning division directly into our ongoing infrastructure initiatives. To reflect this broadened scope, Project Alpha will henceforth be known as Project Omega.",
    
    "2022-12-02": "[Dec 2, 2022 - Slack Export]\nSam: @Alex how is the Initech integration going?\nAlex: It's messy. Their ML models are highly coupled. We are rewriting half of Omega to accommodate it.\nSam: Just get it done before the holidays.",
    
    "2023-08-14": "[Aug 14, 2023 - HR Announcement]\nWe are pleased to announce that Alex is transferring to our European division. Alex will be relocating to London effective September 1st to help establish our overseas presence. Consequently, Sam will be taking over as the Lead for Project Omega. Alex will remain involved in an advisory capacity.",
    
    "2023-09-10": "[Sept 10, 2023 - Email]\nFrom: Alex\nTo: Sam\nSubject: London office\nHey Sam, the weather here in London is terrible compared to NY, but the office is finally set up. Let me know if you need any help with Omega this quarter.",
    
    "2024-02-28": "[Feb 28, 2024 - Board Minutes]\nThe board has voted unanimously to spin off Project Omega into its own independent entity, given its massive success and distinct market fit. The new startup will be named Omegacorp.",
    
    "2024-03-01": "[March 1, 2024 - Omegacorp Launch Document]\nOmegacorp is officially live! Sam has been appointed as the CEO of the new venture. We are also proud to announce our founding Board of Directors, which includes our original visionary, Alex, who will provide strategic oversight. The Omegacorp headquarters will remain in New York."
}

FILLER_SENTENCES = [
    "The engineering team reviewed the latest pull requests and approved the CI/CD pipeline updates.",
    "Marketing is preparing the new Q3 collateral for the upcoming enterprise push.",
    "We noticed a slight increase in latency across the eu-west-1 region, investigating root causes.",
    "The daily standup concluded with no major blockers; everyone is continuing with their sprint tasks.",
    "Lunch catering today was provided by the local deli. Feedback on the sandwiches was generally positive.",
    "Compliance has requested an audit of the new data retention policies before we roll them out.",
    "A minor bug in the frontend authentication flow was patched and deployed to staging.",
    "The quarterly all-hands meeting has been rescheduled to next Thursday due to scheduling conflicts.",
    "Database indexing has completed successfully, reducing average query time by 12%.",
    "Customer support reported a 5% drop in ticket volume this week, likely due to the new FAQ section."
]

def generate_filler_paragraph():
    return " ".join(random.choices(FILLER_SENTENCES, k=random.randint(15, 25)))

def generate_huge_doc(output_path, target_words=150000):
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    current_date = start_date
    total_words = 0
    
    with open(output_path, "w") as f:
        f.write("=== CORPORATE ARCHIVE LOG (2021-2024) ===\n\n")
        
        while current_date <= end_date and total_words < target_words:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Write key event if it exists for this date
            if date_str in KEY_EVENTS:
                f.write(f"{"="*40}\n")
                f.write(f"CRITICAL ARCHIVE ENTRY - {date_str}\n")
                f.write(f"{"="*40}\n")
                f.write(KEY_EVENTS[date_str] + "\n\n")
                total_words += len(KEY_EVENTS[date_str].split())
            
            # Write filler logs for the day (about 100-200 words)
            filler = generate_filler_paragraph()
            f.write(f"[System Log: {date_str} 09:00:00]\n")
            f.write(filler + "\n\n")
            
            filler_2 = generate_filler_paragraph()
            f.write(f"[System Log: {date_str} 14:30:00]\n")
            f.write(filler_2 + "\n\n")
            
            total_words += len(filler.split()) + len(filler_2.split())
            current_date += timedelta(days=1)
            
    print(f"Generated doc with approx {total_words} words at {output_path}")
    print(f"File size: {os.path.getsize(output_path) / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brittle_rag_test_500_pages.txt")
    generate_huge_doc(out_file)
