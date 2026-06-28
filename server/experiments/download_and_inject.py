import urllib.request
import os

# The key story points that test multi-hop RAG reasoning
# We will inject these at specific byte offsets or line numbers.
KEY_EVENTS = [
    "[Jan 12, 2021 - Globex Internal Memo]\nWelcome to the team, Alex! As the newly appointed Lead for Project Alpha, you will be spearheading our cloud migration strategy. We are excited to have you in our New York headquarters. Project Alpha is our biggest bet this year.",
    
    "[March 5, 2021 - Meeting Transcript]\nAlex: \"The cloud migration is going well. We are evaluating several vendors. I'm loving the NY office, by the way, the pizza here is great.\"\nSam: \"Glad to hear it. Let's keep the focus on the Q2 deliverables.\"",
    
    "[Nov 18, 2022 - Press Release]\nGlobex is thrilled to announce the acquisition of Initech. This synergistic merger will allow us to absorb Initech's machine learning division directly into our ongoing infrastructure initiatives. To reflect this broadened scope, Project Alpha will henceforth be known as Project Omega.",
    
    "[Dec 2, 2022 - Slack Export]\nSam: @Alex how is the Initech integration going?\nAlex: It's messy. Their ML models are highly coupled. We are rewriting half of Omega to accommodate it.\nSam: Just get it done before the holidays.",
    
    "[Aug 14, 2023 - HR Announcement]\nWe are pleased to announce that Alex is transferring to our European division. Alex will be relocating to London effective September 1st to help establish our overseas presence. Consequently, Sam will be taking over as the Lead for Project Omega. Alex will remain involved in an advisory capacity.",
    
    "[Sept 10, 2023 - Email]\nFrom: Alex\nTo: Sam\nSubject: London office\nHey Sam, the weather here in London is terrible compared to NY, but the office is finally set up. Let me know if you need any help with Omega this quarter.",
    
    "[Feb 28, 2024 - Board Minutes]\nThe board has voted unanimously to spin off Project Omega into its own independent entity, given its massive success and distinct market fit. The new startup will be named Omegacorp.",
    
    "[March 1, 2024 - Omegacorp Launch Document]\nOmegacorp is officially live! Sam has been appointed as the CEO of the new venture. We are also proud to announce our founding Board of Directors, which includes our original visionary, Alex, who will provide strategic oversight. The Omegacorp headquarters will remain in New York."
]

def generate_huge_doc():
    url = "https://www.gutenberg.org/cache/epub/2600/pg2600.txt" # War and Peace (~3.2 MB)
    print("Downloading War and Peace from Project Gutenberg...")
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        text = response.read().decode('utf-8')
        
    lines = text.split('\n')
    total_lines = len(lines)
    print(f"Downloaded {total_lines} lines of text.")
    
    # Inject the 8 events evenly throughout the book
    interval = total_lines // (len(KEY_EVENTS) + 1)
    
    for i, event in enumerate(KEY_EVENTS):
        insert_index = interval * (i + 1)
        # Ensure we insert between paragraphs
        while insert_index < total_lines and lines[insert_index].strip() != "":
            insert_index += 1
            
        header = f"\n\n{'='*60}\nCRITICAL ARCHIVE ENTRY {i+1}\n{'='*60}\n"
        lines.insert(insert_index, header + event + "\n\n")
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brittle_rag_test_500_pages_gutenberg.txt")
    with open(output_path, "w", encoding='utf-8') as f:
        f.write("\n".join(lines))
        
    print(f"Saved massive doc with injected RAG traps to: {output_path}")
    print(f"File size: {os.path.getsize(output_path) / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    generate_huge_doc()
