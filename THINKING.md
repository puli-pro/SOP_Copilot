# THINKING.md

## 1. Understand the user

### Who is the user?

The primary user is a shop-floor shift supervisor in a manufacturing plant. In the sample documents this is the Hosur plant of Kaveri Precision Components, where a supervisor on the shaft machining line would look after the TX-200 CNC turning centres (CNC-04 to CNC-09) and the operators running them.

The supervisor oversees daily production and makes sure people follow the correct procedures, safety rules and quality standards. They are the link between operators, maintenance, quality control and plant management.

They are not the maintenance engineer, the QC engineer or the safety officer. But during the shift, and especially at night, they are the first person everyone asks on all three topics.

They are usually on the floor, not at a desk, so they need information on a phone or tablet.

### What are their responsibilities?

- Making sure production follows the approved SOPs.
- Watching quality and spotting process deviations.
- Making sure workers follow safety procedures.
- Coordinating maintenance and troubleshooting.
- Helping workers understand the correct procedure.
- Responding to unexpected situations during the shift.
- Making sure documentation and company policies are followed.

### What are they trying to do in the moment?

Their real job is to hit the shift's target without a safety incident and without bad parts going out. Questions from the documents come up in the middle of that work:

- An alarm comes up on a machine and the operator asks if they can reset it and continue.
- A lot of BH-220 bearing housings arrives and someone asks how many pieces to check, or what tolerance applies.
- A technician from the earlier shift has gone home and left a lock on a machine that is needed now.
- A new operator asks how often something has to be checked, and whose job it is.

In each case they need a short, correct answer in under a minute, and then go back to running the line.

### What problems do they face today?

- **Time-consuming searches.** They may have to open several PDFs and search by hand while a machine stands idle.
- **Scattered information.** One task can need two documents. Replacing a hydraulic hose is in the maintenance manual, but its first step points to the lockout procedure.
- **Hard to find the specific answer.** They want one row of one table (a torque, a tolerance, an alarm action), and keyword search does not return the full procedure around it.
- **Pressure during production.** Delays affect output, so there is a pull towards going by memory.
- **Risk of wrong interpretation.** Values are close and easy to mix up: way lube oil is ISO VG 68, hydraulic oil is ISO VG 46. A mistake on a lockout step or on accepting a lot has real consequences.
- **Not sure it is the latest version.** Every page says "Uncontrolled copy when printed. Refer to QMS for the latest version." The incoming inspection SOP changed a lot between Rev 03 and Rev 04 (sample size, where rejected material goes, which form to use). An old printout can be wrong without anyone noticing.
- **The expert is not on shift.** At night the maintenance engineer, QC manager and safety officer are not in the plant.
- **Limited desktop access.** The information is needed while standing at the machine.

### My assumptions

I do not have direct manufacturing experience, so I assumed the following:

1. Supervisors have a smartphone or tablet on the plant Wi-Fi, and are allowed to use it on the floor.
2. The plant already keeps approved documentation as PDFs.
3. The PDF set can include old revisions, as the sample set does.
4. Supervisors want short, direct answers, not long explanations.
5. Answers must be traceable to the source document.
6. The app must say clearly when the documents do not contain the answer.
7. Supervisors can read short answers in English. The first language on the floor may be different; this is a question for the customer.
8. The copilot gives information only. It does not replace the approvals the SOPs require.

Based on this, I decided to build a document-based AI copilot that answers natural-language questions from the plant's documents.

---

## 2. User journey

### My first draft (written before the AI challenge, kept unchanged)

The following is my initial understanding of how a shop-floor supervisor would use the AI copilot.

**Step 1: Open the application**

The supervisor opens the AI copilot using a smartphone, tablet, or computer connected to the application.

The interface should be simple and should not require technical knowledge.

**Step 2: Ask a question**

Instead of manually searching through PDF documents, the supervisor enters a question in natural language.

For example: "What should I do if a machine shows an overheating warning?"

**Step 3: Process the question**

The application receives the question and searches the indexed manufacturing documents for relevant information.

It retrieves the most relevant document sections and provides them as context to the language model.

**Step 4: Generate an answer**

The AI generates a response using the retrieved document information.

The response should be clear, concise, and easy to understand.

**Step 5: Show the source document**

Along with the answer, the application displays the source document used to generate the response.

This allows the supervisor to verify the information instead of blindly trusting the AI-generated answer.

**Step 6: Handle unavailable information**

If the required information is not available in the provided documents, the application should clearly communicate that it cannot find a supported answer.

It should not invent procedures or provide unsupported instructions.

**Step 7: Take action**

Based on the retrieved information, the supervisor can consult the original document and follow the applicable approved procedure.

For critical safety or equipment-related situations, the supervisor should follow established escalation procedures rather than relying solely on the AI copilot.

**What could go wrong?**

| Potential problem | Expected application behavior |
|---|---|
| No relevant information found | Clearly state that the documents do not contain the answer |
| Incorrect document retrieved | Show the source so the supervisor can verify it |
| Ambiguous question | Ask the user to provide more details |
| PDF extraction problems | Report documents that could not be processed |
| AI generates unsupported information | Restrict answers to retrieved document context |
| Network connectivity problems | Show a clear connection or request error |
| Outdated procedure | Display document identification or revision details when available |

The most important consideration is that the application should prioritize reliability and transparency over simply generating an answer.


### Revised journey (after the AI challenge / my reflection in section 3)

After reviewing the AI feedback, I realised that my initial user journey focused more on how the application works internally than on what the supervisor actually needs during a shift.

I revised the journey to focus on speed, reliability, document traceability and safe decision-making.

**The moment I am designing for**

It is 2 AM on the night shift. CNC-06 stops with alarm AL-305. The operator asks the supervisor whether he can reset it and carry on. The maintenance engineer is not in the plant, and the manual is on the office computer. The supervisor has a phone, one free hand and about a minute.

He types "AL-305". Within a few seconds he sees: spindle overload; stop the cycle, check tool wear and cutting parameters, inform the shift supervisor. Under it is the source: MNT-MAN-CNC-02, Rev 02, section 6, page 2, with the exact table row. He tells the operator to check the tool, and the line is running again without anyone being woken up.

The steps below describe the same journey in general terms.

**Step 1: Open the application**

The supervisor opens the AI copilot using a smartphone, tablet or computer.

The interface should provide a simple entry point without requiring the user to understand how document retrieval or AI processing works.

**Step 2: Ask a question**

The supervisor enters a question using natural language. The application should also support short queries, machine alarm codes and technical terms.

For example:
- "AL-104"
- "BH-220 OD tolerance"
- "Who can remove another person's LOTO lock?"
- "How do I replace a hydraulic hose?"

The goal is to make the application useful even when the supervisor has only a few seconds to enter a question.

**Step 3: Understand the question and retrieve relevant information**

The application processes the query and identifies the relevant information from the available manufacturing documents.

It should consider document relevance and revision information rather than relying only on keyword similarity.

For questions involving multiple procedures, the retrieval process should also consider related documents. For example, replacing a hydraulic hose requires consulting both the preventive maintenance manual and the Lockout/Tagout procedure.

While this happens, the supervisor sees that the application is working. A blank screen for ten seconds would make them put the phone away and ask someone instead.

**Step 4: Generate a concise and supported answer**

The application generates an answer using the retrieved document content as context.

The response should prioritise the information the supervisor needs immediately, such as operating limits, inspection tolerances, alarm actions and required procedural steps.

The application should avoid introducing information that is not supported by the available documents.

For safety-critical questions, important warnings, isolation requirements and approval conditions should not be omitted simply to make the answer shorter.

**Step 5: Display source references**

Along with the answer, the application should identify the source document and provide useful reference information, including the document number, revision, section and page number where available.

This is particularly important when multiple revisions of the same SOP exist.

The supervisor should be able to verify the original information without manually searching through an entire PDF.

**Step 6: Handle ambiguity and unavailable information**

If a question is unclear, the application should ask for clarification or present clearly distinguishable alternatives.

If the available documents do not contain sufficient information, the application should explicitly communicate that limitation.

Where possible, it should identify related documents or the appropriate department to consult rather than leaving the supervisor without a next step.

**Step 7: Support the supervisor's next action**

The supervisor uses the retrieved information to understand the applicable procedure and determine the appropriate next step.

The copilot provides information and references; it does not approve rejected material, authorise lock removal, override machine safety controls or replace decisions that require an authorised employee.

For critical maintenance, quality and safety situations, the supervisor must follow the applicable approved procedure and escalation requirements.

**Revised design considerations**

The revised journey introduced several considerations that were missing from my initial design:

| Area | Revised approach |
|---|---|
| Query input | Support short technical queries and alarm codes |
| Document retrieval | Consider relevance and document revision |
| Answer generation | Prioritise concise, source-supported answers |
| Source verification | Provide document number, revision, section and page |
| Cross-document questions | Consider related procedures when required |
| Waiting time | Show that the question is being processed; never a blank screen |
| Missing information | Clearly communicate limitations and suggest the next step |
| Safety | Preserve critical instructions, warnings and approval requirements |
| User experience | Keep the interaction simple and suitable for shop-floor use |

This revised journey is what the app now does. A supervisor can type a bare code such as "AL-305" or "bh220 od" and get the matching table row, with the document, revision, section and page. While the AI works they see a status indicator instead of a blank screen. If the answer is not in the documents the app says so and points to the closest documents and to who to ask. For lockout questions it always shows the rule and its exception together, word for word from the SOP (see section 3 and the biggest challenge in section 5).

The main change in my thinking was that a manufacturing copilot should not be evaluated only by how well it generates answers. It should be evaluated by whether it helps a supervisor find the correct, current and complete information when it matters.

---

## 3. AI challenge

### Objective

After writing my first draft, I asked an AI tool (Claude) to challenge it from the point of view of a skeptical shop-floor supervisor and a skeptical product manager, to find problems I had overlooked. The twelve points below are Claude's critique of my first draft, which I had already written on my own; the reflection that follows is mine.

### My prompt

> I am building an AI copilot for manufacturing shop-floor supervisors. The application uses RAG to answer questions from SOPs, maintenance manuals, and safety documents. Here is my proposed user journey: [the first draft above]. Act as a skeptical shop-floor supervisor and product manager. Challenge my assumptions. Identify usability problems, safety concerns, missing functionality, and situations where the application could fail. Be critical and suggest practical improvements.

### AI feedback (key excerpts)

**As the supervisor**

1. **"Your journey has no moment in it."** There is no time, no machine, no reason I picked up the phone. Your example, an overheating warning, is not in any of the four documents, so your own example ends in "not found". Use a real case: it is 2 AM, CNC-06 shows AL-305, the operator wants to know if he can carry on.
2. **"Steps 3 and 4 are about your system, not about me."** I don't care that it retrieves sections. I care what I see while I wait and how long I wait. A local model can take 10 to 20 seconds. If the screen sits blank I will put the phone away and ask someone.
3. **"I am not going to type a sentence."** With gloves on, next to a running machine, I will type "al104" or "bh220 od". If the app only works with full, well-spelled questions, it does not work for me.
4. **"'Shows the source document' is not enough."** Two of your documents have the same title: Incoming Material Inspection, Rev 03 and Rev 04. A document name does not tell me which one I am reading. I need the revision, the section and the page, and the exact lines, because I will not open a PDF and scroll on a phone.
5. **"'Display revision details when available' is too weak."** The app can answer "draw 5 samples" from Rev 03, with a perfectly correct citation, and be wrong. The current rule depends on lot size. Showing me the revision after the fact puts the checking back on me. The app should answer from the current revision by default.
6. **"'I can't find it' is a dead end."** Then what? Tell me who to ask or what the closest documents are. And if it says "not found" for something I know is in the manual, I will stop using it within a day.
7. **"Your safety line is a disclaimer, not a design."** "Follow escalation procedures" does nothing for me. The dangerous case is a half answer. If I ask who can remove a lock and it says "only the owner", that is true and incomplete: when the owner has gone home there is a procedure needing the Production Manager and the Safety Officer. If I ask how to replace a hydraulic hose and it skips the lockout step, somebody gets hurt.
8. **"Asking me for more details costs me a round trip."** If my question is vague, show me the most likely answer and offer the alternatives as buttons. Don't make me type again.

**As the product manager**

9. **"How will you know it works?"** There is no measure of success in the journey. What is the acceptable rate of wrong answers, of false "not found", and the response time?
10. **"Why would they use it a second time?"** Asking the senior operator is faster than any app. The copilot only wins when nobody is around to ask or the answer has changed recently. Design for those moments.
11. **"You have not checked your assumptions about the floor."** Are phones allowed near the machines? Does Wi-Fi reach there? Do supervisors read English comfortably, or should it answer in Tamil?
12. **"Chat may be the wrong interface."** A QR code on each machine that opens that machine's alarms and maintenance schedule could beat typing. Voice input could beat both. Have you considered them?

### Reflection

**1. Trust and verification** (feedback 4, 5)

I agree that supervisors should not blindly trust AI-generated answers. Showing the source document is important because users need a way to verify the information.

I also realised that showing only the document name is not sufficient, especially when multiple revisions of the same SOP exist. For example, QC-SOP-014 Rev 03 and Rev 04 contain different sampling requirements. An answer retrieved from an older revision could be factually correct according to that document but still be wrong for current operations.

I believe the copilot should prioritize the latest approved document revision and display the document number, revision, section and page number along with the answer. Where possible, it should also highlight the exact supporting text. This makes verification faster and reduces the possibility of following outdated instructions.

**2. Handling missing information** (feedback 1, 6)

I agree that the application should never invent answers when the documents do not contain relevant information. Clearly communicating that information is unavailable is better than generating a potentially misleading response.

However, I also agree that simply displaying "Information not found" is not a good user experience. The application should help the supervisor understand why an answer could not be provided. For example, it could indicate that the uploaded documents do not cover the requested topic or suggest a related document that might contain useful information.

I also realised that a failed retrieval does not necessarily mean the information is absent. The system might fail to identify relevant content because the user entered a short query, an alarm code or an abbreviation. Therefore, the application should be designed to handle different ways of asking the same question before concluding that information is unavailable.

**3. User experience** (feedback 2, 3, 8)

I agree that the interface should be simple and usable on mobile devices. Supervisors may not have time to navigate complex interfaces during production activities.

One important point I had overlooked was that users might not enter complete sentences. A supervisor standing near a machine may simply type something like "AL-104" or "BH-220 OD". Therefore, the application should understand short queries, technical terms and common abbreviations.

I also realised that the application should provide useful feedback while processing a question rather than leaving the screen blank. Responses should be concise, with important values and actions easy to identify.

For ambiguous questions, I considered the suggestion of showing possible alternatives. However, I would prefer to provide a short clarification or clearly separated options rather than immediately presenting an uncertain answer as if it were confirmed.

**4. Safety and operational risks** (feedback 7)

I agree that an AI copilot should support supervisors in finding approved information, not replace established safety procedures or human decision-making.

This feedback made me realise that providing a technically correct but incomplete answer can be more dangerous than providing no answer at all.

For example, when explaining how to replace a hydraulic hose, the application must include the machine isolation requirements, release of stored hydraulic pressure and verification that the pressure gauge reads zero. It should not retrieve only the steps related to removing and replacing the hose while ignoring the Lockout/Tagout procedure.

Similarly, when answering questions about removing another person's lock, the application must include the exceptional lock-removal procedure rather than suggesting that a supervisor can simply remove it.

I believe safety-critical answers should retrieve the complete relevant procedure, preserve important warnings and clearly direct users to the required approvals and escalation steps. The copilot should never make operational decisions on behalf of authorised personnel.

**5. Product questions** (feedback 9, 10, 11, 12)

I agree that a working application should be evaluated using more than just whether it generates an answer. Accuracy, unsupported answers, retrieval failures and response time are important measures of its usefulness.

I also agree that the application must provide a reason for supervisors to use it repeatedly. Its value is not in replacing experienced employees but in making approved information easier to access, particularly when the relevant engineer or specialist is unavailable.

The feedback also highlighted assumptions I had not validated. I had assumed that supervisors could use smartphones or tablets on the shop floor, that Wi-Fi was available and that English was suitable for everyone. These are questions that should be discussed with the actual customer before making final product decisions.

I found the QR code and voice-input suggestions interesting. They could make the application more convenient in a manufacturing environment. However, I would treat them as possible future improvements rather than immediate requirements. I would first make sure that the core question-and-answer experience works reliably.

**What I agreed with**

I agreed with most of the feedback because it highlighted practical problems that I had not considered in my initial design.

The most important points I agreed with were:

- Showing the exact document revision, section and page instead of displaying only the document name.
- Prioritising the latest approved revision to prevent outdated procedures from being used.
- Supporting short queries, alarm codes and technical abbreviations.
- Providing useful feedback while the application processes a question.
- Avoiding incomplete answers, particularly for safety-critical procedures that depend on multiple documents.
- Measuring the application's reliability through answer accuracy, retrieval quality, response time and unsupported-answer handling.
- Validating real shop-floor conditions, including device availability, connectivity and language preferences.

These suggestions helped me think beyond the technical implementation and focus more on how the application would actually be used during a production shift.

**What I disagreed with**

I did not completely agree with the suggestion to always show the most likely answer when a question is ambiguous.

Although this could reduce the number of interactions required, it could also create confusion in a manufacturing environment. For example, if a supervisor asks about an inspection requirement without specifying the material or document revision, showing one assumed answer could result in an incorrect inspection decision.

I believe accuracy should take priority over reducing the number of clicks. The application should ask for clarification or display clearly labelled alternatives when the available context is insufficient.

I also decided not to prioritise QR-based navigation and voice interaction immediately. These features could improve usability, but they would add implementation complexity before I had established that the core document retrieval and answer-generation process was reliable.

**What I changed**

Based on the feedback, I changed my approach from building a simple document-question-answering interface to designing a more reliable manufacturing document copilot.

The main changes I identified were:

- Making document revision awareness an important part of retrieval rather than treating revision information as optional metadata.
- Including document references and supporting sections with generated answers.
- Improving support for short technical queries, machine alarm codes and abbreviations.
- Providing clear responses when information is unavailable instead of allowing the AI to generate unsupported answers.
- Considering related documents when a question involves multiple procedures.
- Giving additional attention to safety-critical questions so that important isolation steps, warnings and approval requirements are not omitted.
- Keeping answers concise and suitable for supervisors accessing the application on mobile devices.

- Not trusting the AI to remember a safety exception. After building the app I saw the small model answer the lockout question with only "each authorised person removes only their own lock" and leave out the owner-absent procedure, which is exactly the half answer the critique warned about. I changed the app so that this is enforced in code instead of asked of the model (details in section 5).

I deliberately kept advanced features such as voice interaction, QR-based machine navigation, multilingual support and offline access outside the immediate scope. I consider these useful future improvements, but I wanted to establish the reliability of the core functionality first.

Overall, this challenge helped me understand that building an AI copilot is not just about retrieving documents and generating responses. It is about ensuring that the information is relevant, current, complete and trustworthy enough to support real decisions.

---

## 4. The improvement I added, and why I chose it

**Selected improvement:**

Revision-aware document identification and visibility. The copilot distinguishes between current and superseded document revisions and makes that visible to the supervisor through source references, revision details and a superseded-document warning.

**Problem identified:**

While analysing the provided documents, I found that QC-SOP-014 was included in two revisions: Rev 03 and Rev 04. Although both documents have the same title and document number, several important operational instructions have changed.

For example, Rev 03 specifies a fixed sample size of five pieces for every incoming lot, whereas Rev 04 introduces a sampling plan based on lot size. Other changes include making the Material Test Certificate mandatory, moving rejected material to Quarantine Cage Q1, replacing the paper inspection form with digital form QF-07A and introducing a four-hour escalation requirement for the Supplier Quality Engineer.

This creates a significant problem for a conventional document-based RAG system. Both revisions contain relevant information, so a similarity-based retrieval process could retrieve an older instruction and generate an answer that appears correct but is no longer applicable.

I felt that displaying a citation alone would not solve this problem. The application needed to understand which revision should be used before generating an answer.

**My solution:**

I chose revision awareness as the primary user-facing improvement.

The document ingestion process extracts the document number, revision and effective date from each PDF. This information is stored as metadata alongside the extracted document sections.

The retrieval distinguishes between current and superseded revisions. Current documents are used by default, while older revisions are retrieved only when a user explicitly asks about a previous version or a historical change.

The user-facing improvement is that every answer shows the document revision and effective date. Superseded documents carry a clearly visible red warning so that supervisors can recognise when an older procedure is being referenced.

**Why I selected it:**

I selected this improvement because it addresses a real problem in the supplied documents rather than introducing an additional feature simply to make the application look more advanced.

In a manufacturing environment, following an outdated inspection procedure can result in incorrect quality decisions. Similarly, using an outdated maintenance or safety instruction can introduce operational risks.

I also wanted the improvement to demonstrate that document retrieval requires more than finding semantically similar paragraphs. The application needs to understand document structure and metadata before deciding which information should be used.

**How it improves the experience:**

The supervisor does not have to manually compare multiple PDFs to determine which revision is relevant.

Instead, the application uses the current revision and shows the revision details directly with the answer.

This improves trust, reduces the possibility of using outdated instructions and makes the source information easier to verify.

For example, when I ask the running app how many samples must be inspected from a lot of 200 pieces, it answers 13 from Rev 04, not the five samples specified in Rev 03. In my evaluation none of the 17 questions that did not ask about an old revision used a Rev 03 source.

The revision information also makes it easier to understand why an answer has been generated and which version of the procedure supports it.

**Implementation details:**

This is how it is built:

- During ingestion, the application extracts the document number, revision and effective date from the PDF header.
- Each document section stores its revision metadata and a status identifying it as current or superseded.
- The retrieval process uses both vector similarity and keyword matching, with Reciprocal Rank Fusion (RRF) to combine the results.
- Superseded document sections are excluded from normal retrieval unless the question explicitly refers to an older revision or a historical change.
- The response includes source information such as document number, revision, section, page number and supporting text.
- Superseded sources display a red warning in the source card, and a note such as "answered from Rev 04 (current); Rev 03 is superseded and was not used" appears with the answer.

The app uses PyMuPDF for document extraction, BGE-small-en-v1.5 for embeddings, BM25 for keyword retrieval, NumPy for cosine similarity, Ollama (`qwen2.5:3b`) for local language-model inference, FastAPI for the API and a plain HTML/CSS/JS page for the interface.

One honest limit: "current" means "the highest revision number found in the PDFs I was given". The app cannot know whether the plant has issued a newer revision that is not in the folder. That is why one of my customer questions is about an authoritative source of document status.

---

## 5. Final reflection

### What I would build next

The current project focuses on making manufacturing documents searchable and providing answers grounded in their content. If I were to take this further, I would focus on making the copilot more useful in a real manufacturing environment.

Some of the improvements I would consider are:

- **Filtering by machine and area:** With hundreds of SOPs, the application should allow supervisors to narrow down information based on their production line, machine or department before retrieving relevant content.
- **Document lifecycle integration:** Instead of identifying current and superseded documents only through revision information extracted from PDFs, I would integrate with the plant's QMS to retrieve the officially approved document status.
- **Multilingual support:** Supervisors should be able to ask questions and receive answers in their preferred language, while retaining references to the original English document.
- **Feedback review:** the app already stores a thumbs up or down for each answer, linked to the full trace of that question. The next step is a screen where an engineer reviews the "not helpful" ones and turns them into new evaluation questions.
- **A bigger model, measured:** I chose a 1.9 GB model so the app runs on one laptop. I did not have time to test a 7B or 8B model on the same evaluation. I would run it and compare, rather than assume it is better.
- **More general exception handling:** the app only recognises an exception when it is written as its own section with a telling heading. Real SOPs also hide exceptions inside paragraphs and tables.
- **Conversation history:** Supervisors should be able to revisit previous questions and share relevant information during shift handovers.
- **Authentication and access control:** Users should only be able to access documents and information appropriate to their roles and responsibilities.
- **Offline and low-connectivity support:** Since network connectivity can be inconsistent on manufacturing floors, I would explore caching frequently accessed information and providing a useful experience during temporary network interruptions.

I would prioritise these improvements based on actual customer feedback rather than implementing all of them at once.

### What I am unsure about

I have built and measured the app, but several things remain uncertain.

- **Evaluation dataset size:** My evaluation has 24 questions (18 answerable, 6 not) across seven pages of source documents. It found real bugs, and I also tuned the app while looking at it, so the scores (for example 89% of key facts correct) are optimistic. It cannot establish production-level reliability.
- **Retrieval reliability at scale:** The current document collection is small. I am unsure how retrieval performance will change when the system contains hundreds of documents with overlapping terminology and similar procedures.
- **Table interpretation by a small model:** This was not hypothetical. The 1.9 GB model said spindle runout is checked "quarterly" when the table says monthly, and it dropped a trailing zero from a tolerance (0.05 instead of 0.050). Two fixes helped (giving the model each row as "Header: value" text, and a check that restores dropped digits), but I cannot promise it will never misread a table I have not tested.
- **Bare codes:** a query such as "AL-305" still gets the action ("stop cycle, check tool wear") without the meaning ("spindle overload") in two of my test questions.
- **Document lifecycle:** I do not know how frequently the plant updates its SOPs, how superseded documents are managed or whether an authoritative system identifies the currently approved revision.
- **Multi-plant requirements:** It is unclear whether the application should eventually support multiple plants, each with different procedures and document permissions.
- **Answer detail:** Different situations may require different levels of detail. An alarm-related question may need a short action, whereas a maintenance procedure may require several steps and safety precautions.
- **Security and compliance:** I would need to understand the plant's requirements for document access, employee authentication, audit logs and handling sensitive operational information.

These are areas where implementation experience and customer feedback would be more valuable than making assumptions during development.

### Questions I would ask the customer

Before extending the application beyond the assignment, I would want to understand the actual working environment and its requirements.

1. How do supervisors currently search for SOPs and manuals, and approximately how long does it take them to find an answer?
2. Which questions or operational problems occur most frequently during a shift?
3. Are old document revisions stored alongside current ones? Is there an authoritative system that identifies the approved revision?
4. Which devices are permitted on the shop floor, and is Wi-Fi consistently available near the machines?
5. Which languages do supervisors and operators prefer to use when searching for technical information?
6. What should the application do when a question is not covered by the available documents? Which department or person should it direct the supervisor to?
7. Which procedures are safety-critical and require additional warnings, approvals or escalation?
8. What level of answer accuracy and response time would the plant consider acceptable?
9. Apart from PDFs, what other document formats are used, such as scanned documents, engineering drawings and spreadsheets?
10. Does the plant require different document access permissions for operators, supervisors, maintenance engineers and QC personnel?

I believe understanding these requirements would help determine which features should be prioritised and which architectural decisions need to change before deploying the system in a production environment.

### Biggest technical challenge and how I handled it

**The biggest challenge: getting a small local model to give a complete answer on safety-critical text.**

Retrieval turned out to be the easier half. Reading the PDFs first let me choose section-based chunking, keep tables whole, handle the Rev 03 / Rev 04 conflict, and combine keyword and vector search so that codes such as AL-104 or BH-220 are found. All five sample questions retrieved the right section in the top four on the first run.

The hard part came when I connected the model (`qwen2.5:3b`, 1.9 GB, chosen so it runs on one laptop). Its first real answers had four problems:

1. **A half answer on lockout.** "Who is allowed to remove a lockout lock?" got only "each authorised person removes only their own lock". The owner-absent procedure (the Production Manager and the Safety Officer must both authorise) was missing, even though that section was in the text it was given. This is exactly what the AI critique of my journey warned about.
2. **A wrong fact from a table.** It said spindle runout is checked "quarterly" instead of monthly.
3. **A changed tolerance.** It wrote `+/- 0.05` for `+/- 0.050`.
4. **A wrong citation, and a 95-second first answer** (the model loading cold).

What I tried, including what did not work:

- Stricter prompt rules and an extra "exceptions" field in the model's answer. This helped a little and did not fix the lockout answer.
- Giving the model each table row as "Header: value" text instead of a Markdown grid, and a check that restores digits the model drops. Key facts went from 69% to 81% on my evaluation, and the runout and tolerance answers became correct.
- A citation check that only accepts a source if the answer text really appears in it. My first version was too strict and made the app refuse questions it could answer (key facts fell to 62%), so I changed the rule and re-measured.
- A rule that moved "barely used" safety sections into an "also read" list. It picked the wrong section on the lockout question, so I removed it rather than ship something I could not trust.
- Loading the model when the server starts, which removed the 95-second first answer.

What finally worked was to stop asking the model to be complete and make the app enforce it. At ingest, the app detects sections that are exceptions from their headings (for example "Removal of a Lock When the Owner Is Absent") and links each to the rule it qualifies. At answer time, whenever either half is cited, both are shown word for word under the answer, and both are given to the model. In my evaluation the exception was shown in 2 of 2 lockout questions, while the model's own answer text contained it in 0 of 2. It showed up on none of the unrelated questions. Along the way I also fixed a case where the model contradicted itself ("not answerable" while writing the correct exception), which had made the app say "not found" on a safety question the documents do answer.

Final numbers from `eval/results.md` (24 questions): key facts 16/18, citations 18/18, 0 of 6 unanswerable questions answered, 0 of 18 answerable questions refused, 0 of 17 using the old revision. I treat these as a sanity check, not proof, because I tuned the app while looking at these same questions.

**Other problems while building and deploying**

- **Unreliable network.** `ollama pull` failed twice with a TLS timeout and then "no such host" because the Wi-Fi DNS kept dropping. The download resumes where it stopped, so I ran it in a retry loop. The same network problem made the server hang at startup trying to reach huggingface.co for a model that was already on disk, so the app now loads the local copy first. This matters for a plant network with no internet.
- **A silent bug in a safety check.** I wrote a regular expression in a Python string with `\b`, which Python turned into a backspace character. The check for codes that are in no document (for example AL-999) silently never fired, so the app tried to answer. I found it only because I tested AL-999 and CNC-12 and they were not refused.
- **Stale page on the phone.** The browser kept showing an old version of the interface after I changed it, so the server now sends no-cache headers for the interface files.
- **Dependency install and a restart.** `pip` failed on a Windows file lock and needed a retry, and Ollama had stopped overnight (I did not find out why) in the middle of an evaluation run. I only noticed because two answers suddenly looked wrong, so I re-ran the whole evaluation after restarting it. Response time also varied (about 2.5 seconds on a good run, up to 22 seconds on a slow one).
- **Opening it from the phone:** **[Add after the phone test: what you saw, and what you had to change, for example the Windows firewall rule for port 8000 and the "Public" network profile.]**

### Overall reflection

This assignment helped me look at RAG development from a product and engineering perspective rather than focusing only on the language model and retrieval pipeline.

My main takeaway is that a manufacturing copilot needs more than semantic search and answer generation. It needs to understand document structure, revision information, technical terminology and the relationships between procedures.

I also realised that choosing the right architecture is not about including every available technology. For this project, I deliberately avoided adding a vector database, reranker, OCR pipeline and additional orchestration frameworks because the supplied documents are small, digitally readable and structurally organised. I wanted each component to solve a specific problem rather than introduce unnecessary complexity.

My approach was to first understand the user, study the source documents, identify the risks, compare architectural options, then build the app and measure it. The result uses section-aware chunking, table preservation, hybrid retrieval, revision filtering, source-grounded answers and, for safety rules, required evidence that the app shows itself.

The most useful lesson was about trust. A small model will sometimes give a fluent, partly right answer, and a prompt asking it to "include exceptions" did not reliably work. For anything safety-related I now prefer a rule in code that I can test over a request to the model that I can only hope for.

I also recognise the limitations of the current scope. Seven pages of sample documents cannot represent the complexity of a real manufacturing knowledge base, and a small evaluation dataset cannot establish production-level reliability.

Overall, this project reinforced my belief that building a useful AI application requires more than knowing how to integrate an LLM or implement RAG. It requires understanding the user's environment, identifying where the system can fail, making deliberate engineering trade-offs and being transparent about what has and has not been validated.

I would consider the current architecture a foundation that can be extended and evaluated further with real manufacturing documents and feedback from actual shop-floor supervisors.
