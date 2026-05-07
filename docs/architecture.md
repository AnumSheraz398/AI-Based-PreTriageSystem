# System Architecture

## Purpose

This document describes the starter multi-agent architecture for the AI-Assisted Pre-Triage System.

## Agents

- Intake Agent: cleans and validates intake payloads
- RAG Agent: retrieves top protocol chunks (simulated ChromaDB)
- Triage Agent: assigns urgency (1-5) with reasoning
- Explanation Agent: returns Urdu/English patient explanation

## Flow

1. Patient submits intake (text/voice simulated)
2. Backend validates mandatory fields
3. RAG returns relevant protocol chunks
4. Triage agent computes urgency and reason
5. Safety rules can override urgency
6. Routing logic maps urgency/symptoms to department
7. Explanation agent generates Urdu patient message
8. Decision and metadata are audit logged

## Hard Safety Rules (Starter)

- Chest pain + breathlessness => urgency 5
- Unconscious patient => urgency 5
- Severe bleeding => urgency 5
