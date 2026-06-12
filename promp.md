# AI Release Manager - Full Project Specification

Build a production-ready application called "AI Release Manager".

## Goal

Create an AI-powered release management platform that connects to GitLab repositories, analyzes commits and issues, generates release notes using an LLM, orchestrates the workflow with LangGraph, and publishes the results to Slack.

The project should be portfolio-quality and demonstrate:

* Agentic workflows
* LangGraph orchestration
* GitLab API integrations
* Slack integrations
* LLM-powered summarization
* Production-grade backend architecture
* Modern React frontend

---

## Tech Stack

### Backend

* Python 3.12+
* FastAPI
* LangGraph
* LangChain
* Pydantic
* SQLAlchemy
* PostgreSQL
* GitLab API
* Slack SDK

### AI

Use one provider:

Option A:

* OpenAI GPT-5

Option B:

* Google Gemini 2.5 Pro

The architecture should allow switching providers through configuration.

### Frontend

* React
* Vite
* TypeScript
* Tailwind CSS
* shadcn/ui

### Infrastructure

* Docker
* Docker Compose
* Environment variables
* Structured logging

---

# Main Workflow

The application must implement a LangGraph workflow.

The graph should contain the following nodes:

1. Fetch Release Data
2. Fetch GitLab Issues
3. Fetch GitLab Merge Requests
4. Analyze Changes
5. Generate Release Notes
6. Review Output
7. Publish To Slack
8. Persist Release

The workflow must support retries and error handling.

---

# GitLab Integration

Allow users to:

* Connect a GitLab repository
* Store GitLab token securely
* Select project
* Select release range

Examples:

* Tag v1.0.0 -> v1.1.0
* Last 30 days
* Last sprint

Fetch:

* Commits
* Merge Requests
* Issues
* Labels
* Authors

---

# AI Analysis

The LLM must classify changes into categories:

* Features
* Bug Fixes
* Performance Improvements
* Security Updates
* Refactoring
* Infrastructure
* Documentation

For each change:

Generate:

* Short summary
* Business impact
* Technical impact
* Risk level

Risk Levels:

* Low
* Medium
* High

---

# Agent Architecture

Implement multiple agents using LangGraph.

## Repository Analyst Agent

Responsibilities:

* Understand commits
* Group related changes
* Detect themes

## Release Writer Agent

Responsibilities:

* Create release notes
* Produce executive summary
* Produce technical summary

## QA Agent

Responsibilities:

* Validate generated release notes
* Detect hallucinations
* Ensure every statement is traceable to source data

## Slack Publisher Agent

Responsibilities:

* Format Slack message
* Publish release
* Return publication URL

---

# RAG Layer

Implement Retrieval-Augmented Generation.

Sources:

* Issues
* Merge Requests
* Commit Messages
* Previous Release Notes

Use:

* LangChain
* Vector Store

The system should retrieve relevant historical context before generating release notes.

---

# Release Note Formats

Generate:

## Executive Version

For managers.

Example:

* High-level summary
* Business outcomes
* Major improvements

## Technical Version

For engineers.

Include:

* Issues fixed
* Architecture changes
* Performance improvements
* Dependencies updated

## Markdown Version

Ready to publish.

## Slack Version

Optimized for Slack formatting.

---

# Slack Integration

Allow users to:

* Connect Slack workspace
* Select channel

Examples:

#engineering

#product

#releases

Support:

* Markdown formatting
* Thread replies
* Release links

---

# Frontend Screens

## Dashboard

Show:

* Connected repositories
* Recent releases
* Release generation metrics

## Repository Page

Show:

* Repository details
* Last releases
* Generate release button

## Release Builder

Show:

* Release range selector
* AI configuration
* Preview

## Release Viewer

Show:

* Generated notes
* Source commits
* Source issues
* Slack publication status

---

# Metrics

Track:

* Release generation time
* Number of commits analyzed
* Number of issues analyzed
* Slack publications
* Estimated documentation hours saved

Display charts on dashboard.

---

# Database Models

Create models for:

User
Repository
Release
Commit
Issue
MergeRequest
SlackWorkspace
GenerationLog

---

# API Endpoints

POST /repositories/connect

GET /repositories

POST /releases/generate

GET /releases

GET /releases/{id}

POST /slack/publish

GET /metrics

---

# Security

Implement:

* JWT Authentication
* Encrypted API tokens
* Rate limiting
* Input validation
* Audit logging

---

# Portfolio Requirements

The codebase should demonstrate:

* Clean Architecture
* SOLID principles
* Type hints everywhere
* Unit tests
* Integration tests
* Repository pattern
* Service layer pattern

---

# Deliverables

Generate:

1. Complete folder structure
2. Database schema
3. Backend implementation
4. LangGraph workflow
5. GitLab integration
6. Slack integration
7. React frontend
8. Docker setup
9. README
10. Example screenshots/mockups

The project should be structured as if it were a real internal tool used by a technology company.
