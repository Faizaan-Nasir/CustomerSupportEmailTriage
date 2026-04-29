# Project Documentation

## Overview

This project was built starting from an idea that I explored independently, and then developed further with the help of AI tools during documentation and implementation.

The idea came from observing how frustrating customer support interactions usually are. Most of the delay does not come from solving the issue itself, but from the repeated back-and-forth between the customer and the support agent. Customers are expected to provide all relevant information in one message, but that rarely happens. As a result, agents keep asking for missing details, which slows everything down.

This project focuses on reducing that inefficiency.

---

## Problem Understanding

The main issue I identified was straightforward:

Customers often send incomplete information in their initial query. Because of this, support agents need multiple follow-ups just to gather the required details before they can even begin solving the issue.

This creates:
- Delays in resolution
- Increased workload for agents
- A frustrating experience for customers

Instead of trying to make responses faster, the idea was to reduce the number of unnecessary responses altogether.

---

## Core Idea and Approach

Once the problem was clear, the solution followed naturally and did not take much time to structure.

The system introduces a few key ideas:

### Automated Response System

The system does not immediately attempt to resolve the issue. Instead, it first checks whether all required information is present.

If something is missing:
- It asks the customer for specific details in a structured way
- This ensures that future responses are more meaningful
- It significantly reduces repeated back-and-forth communication

### Action Plan for Support Agents

Alongside automation, I introduced a structured approach for agents:
- Helps handle common or trivial complaints more efficiently
- Suggests when an issue should be escalated
- Encourages thinking in terms of preventing similar issues in the future, not just resolving the current one

### Time-Based Urgency

Another idea was to increase urgency over time:
- Requests that remain unresolved gradually become more important
- This avoids situations where certain issues are delayed indefinitely
- Effectively prevents starvation of tickets

These ideas were part of my own design and were decided early in the process.

---

## Use of AI During the Project

AI tools were used as support throughout the project, especially for structuring and accelerating development, but not for originating the core idea.

### Idea Validation

After deciding on the idea, I used ChatGPT to:
- Identify potential challenges
- Compare different approaches
- Eliminate ideas that would not be feasible within the given time

This helped narrow down the direction quickly.

---

## Documentation Process

### Proposed Solution Document

I used ChatGPT to generate a structured version of my idea:
- This became `Proposed_Solution.md`
- It was created section by section
- Each section was reviewed and corrected manually

The focus here was to ensure:
- Nothing important was missing
- The logic stayed consistent with the original idea

### Technical Document

Next, I asked for a technical approach.

The initial output suggested general tools (like PostgreSQL), but it lacked specificity. At this stage, I refined the approach based on my own experience.

I enforced the use of:
- Supabase instead of a generic database setup
- FastAPI for backend
- React (Vite) for frontend
- Docker for containerization
- Gemini (Google AI Studio) for LLM capabilities

After finalizing the stack, I again used ChatGPT to generate:
- `technical_document.md`
- Built section by section
- Structured clearly so it could be easily understood or even processed by another system if needed

---

## Challenges Faced

A few practical challenges came up during the implementation phase.

### Arabic LLM Support

One of the requirements was to support Arabic directly:
- I did not want to rely on translation-based approaches
- Finding a suitable model for this took more effort than expected

### Email Integration Attempt

I attempted to simulate a real-world workflow using email:
- Set up a prototype customer support email
- Tried integrating with Gmail API and OAuth 2.0

However:
- This introduced a lot of complexity
- Authentication and setup required more time than available
- This part could not be fully completed within the deadline

---

## Implementation

For the actual development, I used a mix of tools to speed up coding and debugging.

These included:
- CodeX
- GitHub Copilot
- Gemini CLI

They were mainly used for:
- Writing parts of the implementation
- Fixing bugs that came up
- Adding smaller features more efficiently

At the same time:
- The structure, flow, and decisions were guided manually
- AI tools were used to assist, not to define the system

Additional features like:
- Arabic support
- Evaluation metrics
- Threshold-based logic

were added later once the base system was stable.

---

## Time Breakdown

The project was completed within a relatively short timeframe:

- About **1 hour** to finalize the idea and direction  
- About **1 hour** to generate and refine documentation  
- Around **4 hours (in parts)** to build the working prototype  

After getting a working prototype, an additional 2 hours had been spent on adding additional features, making the front-end look natural, and introducing evaluation metrics for the project.

---

## Tech Stack

### Backend
- FastAPI

### Database
- Supabase (PostgreSQL-based)

### Frontend
- React (Vite)

### AI / LLM
- Gemini (Google AI Studio)

### Tools
- Docker
- CodeX
- GitHub Copilot
- Gemini CLI

---

## System Performance and Future Outlook

### Current Strengths
The prototype already demonstrates several robust capabilities:
- **Multilingual Support:** Handles English and Arabic natively with high contextual accuracy, avoiding the pitfalls of machine translation.
- **Urgency-Driven Triage:** Effectively prioritizes high-stakes issues (like security threats or billing errors) for immediate human escalation.
- **Cautious Interpretation:** A key design feature is that the LLM is instructed to side with a **lower confidence score** when it is unsure about a decision. This "cautious-by-default" approach is a significant advantage, as it prevents the system from taking incorrect automated actions on ambiguous tickets, instead opting to ask the customer for clarifying details.
- **Invoice/Bill Suggestion:** To further reduce back-and-forth, if the system identifies three or more pieces of missing information, it intelligently suggests that the customer provide a copy of their bill or invoice. This is often the easiest way for customers to provide all necessary details at once.
- **Subject-Line Awareness:** Intelligent extraction of entities from both the subject and body reduces redundant back-and-forth.

### Areas for Improvement
- **Edge-Case Confidence:** While generally cautious, the system can sometimes exhibit overconfidence when latching onto emotional keywords in messages that otherwise lack factual data. Further prompt engineering is needed to enforce stricter "drop confidence" rules.
- **Full Email Integration:** Completing the OAuth 2.0 flow for direct Gmail/Outlook integration would move the project from a simulator to a production-ready tool.

### Future Area of Improvement: LLM Fine-tuning
A major next step for this project would be the **fine-tuning of the underlying LLM**. By training the model on specific, historical support data from a particular retail domain, we could:
- Improve the accuracy of domain-specific entity extraction.
- Align the "intent" and "category" labels more closely with a specific company's internal taxonomy.
- Reduce the computational cost and latency by using smaller, specialized models that perform as well as (or better than) larger general-purpose models for this specific task.

---

## Final Notes

This markdown file was also generated with the help of ChatGPT, mainly to reduce time spent on formatting.

Overall, the project combines:
- Independently developed ideas and design decisions
- AI-assisted documentation and implementation

The focus throughout was on solving a real and practical problem in a way that could be implemented within a limited amount of time.