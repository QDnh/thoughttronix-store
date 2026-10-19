---
name: implement
description: Implement one approved phase from a PRD and plan using feedback loops.
argument-hint: "@prd/<feature>.md @plans/<feature>.md implement phase <N>"
disable-model-invocation: true
---

# Implement

## 1. Understand the Phase

Read the referenced PRD and plan. Explore the codebase to understand the relevant files,
patterns, and conventions. If the request does not identify a phase, ask which one.

Implement only that phase. Do not begin the next one.

## 2. Implement the Phase

Ask the user whether to run the /tdd skill.
If yes, run the /tdd skill before starting implementation of the specified phase.
If no, skip the /tdd skill and move on to implementing the specified phase. 

## 3. Run Feedback Loops

Run the pytest suite to ensure all tests passed.
Run ruff checks.

## 4. Manual Verification

Explain how the phase can be manually verified in the browser.
Wait for the user to tell you to continue.

## 5. Finish the Phase

Ask the whether to append PROMPTS.md.
If yes, append a session log to PROMPTS.md at the repo root, under today's date, 
newest entry at the top; record every prompt the user gave you this session, 
in order, including any corrections; end the entry with a short summary: the outcome, 
any places where the user deviated from a recommended answer or asked follow-up questions, 
and anything that went sideways.

Ask the user whether to commit the changes to GitHub.
If yes, ask for a title for the commit.