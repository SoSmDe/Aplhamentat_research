# Ralph Deep Research - Storage package
"""
Data persistence layer for the Ralph research system.

Components:
- Database: SQLite database connection and operations
- SessionManager: Session state management with Ralph Pattern persistence
- FileStorage: Report file storage and retrieval

Tables:
- sessions: Session metadata and status
- session_data: JSON-encoded intermediate results
- session_files: Generated reports with metadata
"""
