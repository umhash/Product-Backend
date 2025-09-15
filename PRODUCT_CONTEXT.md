# Product Context: Student Study Copilot

## Overview
Student Study Copilot is a web application for students applying to UK universities.  
It has two parts:
- **Backend:** FastAPI (Python, async, modular, PostgreSQL, SQLAlchemy).
- **Frontend:** Next.js (React, TypeScript, TailwindCSS).

## Core Features
1. **User Authentication**
   - Register/Login with JWT authentication.

2. **Chatbot (Student Consultant)**
   - Guides students about admission process in UK universities.
   - Answers relevant admission-related questions.

3. **Eligibility Checker**
   - Collects student academic/personal data.
   - Determines eligibility for admission.
   - Shows missing requirements if not eligible.

4. **University Application**
   - Shows eligible universities.
   - Student selects universities and clicks **Apply**.
   - Admin receives application and can request offer letter.
   - System tracks offer letter request status.
   - When offer letter is received, admin uploads to system.
   - Student can view progress and download offer letter when available.

5. **Document Upload & Interview Scheduling** *(Enhanced)*
   - Student sees required documents for initial application.
   - Student uploads documents.
   - **NEW:** After offer letter received, admin configures interview-specific documents.
   - **NEW:** Admin selects required document types from existing document library.
   - **NEW:** Student uploads additional documents required for interview.
   - **NEW:** Once all interview documents uploaded, student can request interview.
   - **NEW:** Admin receives interview requests and can schedule manually with date, time, location, and meeting link.
   - **NEW:** System tracks interview status: documents_required → requested → scheduled.
   - Student sees real-time interview status and progress.
   - **NEW:** Student document manager shows all documents across applications.
   - **NEW:** After interview conducted, admin marks result as pass/fail with notes.
   - **NEW:** If pass: enables CAS application. If fail: application rejected.

6. **CAS Application** *(Complete Flow)*
   - **STEP 1:** After interview passes, admin configures required CAS documents.
   - **STEP 2:** Admin selects document types needed for CAS application.
   - **STEP 3:** Student sees required CAS documents and uploads them individually.
   - **STEP 4:** Student submits all CAS documents for processing.
   - **STEP 5:** Application status changes to 'cas_application_in_progress'.
   - **STEP 6:** Admin manually processes CAS application externally.
   - **STEP 7:** Admin uploads received CAS document to system.
   - **STEP 8:** When CAS uploaded, visa application is automatically enabled.
   - **STEP 9:** Student can download CAS document once available.

7. **Visa Application** *(Complete Flow)*
   - **STEP 1:** After CAS received, admin configures required visa documents.
   - **STEP 2:** Admin selects document types needed for visa application.
   - **STEP 3:** Student sees required visa documents and uploads them individually.
   - **STEP 4:** Student submits all visa documents for processing.
   - **STEP 5:** Student can now click "Apply for Visa" button.
   - **STEP 6:** Application status changes to 'visa_application_in_progress'.
   - **STEP 7:** Admin manually processes visa application externally.
   - **STEP 8:** Admin uploads received visa document to system.
   - **STEP 9:** Application status changes to 'completed'.
   - **STEP 10:** Student can download visa document and application is complete.

8. **Completion**
   - Student's application process is complete after receiving visa.

## Application Status Flow *(Complete)*
```
draft → submitted → under_review → offer_letter_requested → offer_letter_received 
→ interview_documents_required → interview_requested → interview_scheduled 
→ accepted/rejected

CAS Flow (after accepted):
accepted → cas_documents_required → cas_application_in_progress → [CAS received]

Visa Flow (after CAS received):
[CAS received] → visa_documents_required → visa_application_ready 
→ visa_application_in_progress → completed

Complete Flow Logic:
- Interview PASS → CAS flow enabled
- Interview FAIL → Application rejected  
- CAS received → Visa flow enabled
- Visa received → Application completed
```

## New Database Models *(Complete)*
- **Application** (enhanced): Added interview, CAS, and visa fields
  - Interview: `interview_location`, `interview_meeting_link`, `interview_result`, `interview_result_notes`, `interview_result_date`
  - CAS: `cas_documents_configured_at`, `cas_documents_submitted_at`, `cas_applied_at`, `cas_received_at`, `cas_filename`, `cas_original_filename`, `cas_path`, `cas_size`, `cas_notes`
  - Visa: `visa_application_enabled_at`, `visa_documents_configured_at`, `visa_documents_submitted_at`, `visa_applied_at`, `visa_received_at`, `visa_filename`, `visa_original_filename`, `visa_path`, `visa_size`, `visa_notes`
- **ApplicationInterviewDocument**: Tracks interview-specific document requirements per application
- **ApplicationCASDocument**: Tracks CAS-specific document requirements per application
- **ApplicationVisaDocument**: Tracks visa-specific document requirements per application
- **DocumentType**: Existing model used for document selection across all flows

## New API Endpoints *(Complete)*
**Admin Interview Endpoints:**
- `POST /admin/api/applications/{id}/configure-interview-documents`
- `GET /admin/api/applications/{id}/interview-documents`
- `POST /admin/api/applications/{id}/schedule-interview`
- `POST /admin/api/applications/{id}/interview-result`

**Admin CAS Endpoints:**
- `POST /admin/api/applications/{id}/configure-cas-documents`
- `GET /admin/api/applications/{id}/cas-documents`
- `POST /admin/api/applications/{id}/upload-cas`
- `GET /admin/api/applications/{id}/cas/download`

**Admin Visa Endpoints:**
- `POST /admin/api/applications/{id}/configure-visa-documents`
- `GET /admin/api/applications/{id}/visa-documents`
- `POST /admin/api/applications/{id}/upload-visa`
- `GET /admin/api/applications/{id}/visa/download`

**Student Interview Endpoints:**
- `GET /applications/{id}/interview-documents`
- `POST /applications/{id}/upload-interview-document`
- `POST /applications/{id}/request-interview`

**Student CAS Endpoints:**
- `GET /applications/{id}/cas-documents`
- `POST /applications/{id}/upload-cas-document`
- `POST /applications/{id}/submit-cas-documents`
- `POST /applications/{id}/apply-cas`
- `GET /applications/{id}/cas/download`

**Student Visa Endpoints:**
- `GET /applications/{id}/visa-documents`
- `POST /applications/{id}/upload-visa-document`
- `POST /applications/{id}/submit-visa-documents`
- `POST /applications/{id}/apply-visa`
- `GET /applications/{id}/visa/download`

## Technical Guidelines
- **Backend**
  - Folder structure: `routers/`, `schemas/`, `services/`, `db/`.
  - Use async FastAPI routes.
  - Use Pydantic for request/response schemas.
  - Database: PostgreSQL via SQLAlchemy ORM.
  - Use dependency injection for DB sessions.
  - Use HTTPException for error handling.
  - JWT authentication.

- **Frontend**
  - Folder structure: `components/`, `pages/`, `hooks/`, `utils/`.
  - Next.js + TypeScript + TailwindCSS.
  - Use React Query (or SWR) for API calls.
  - Small, reusable components.
  - Server Components where possible (Next.js 13+).
  - Auth handling via JWT tokens.

- **Testing**
  - Backend: pytest.
  - Frontend: Jest + React Testing Library.

## Rules
- Always prefer simple, modular, production-ready code.
- Avoid unnecessary libraries and complexity.
- Use type hints in Python + TypeScript.
- Only generate code when asked, no explanations unless requested.
