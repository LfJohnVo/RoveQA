-- A separate database for the test suite.
--
-- The suite creates and drops tables freely; pointed at the application's database it
-- destroys whatever a developer was looking at, and the symptom ("my project vanished")
-- looks nothing like the cause.
--
-- Runs only when the data volume is created. An existing deployment needs:
--   docker compose exec postgres createdb -U agentic agentic_qa_test
SELECT 'CREATE DATABASE agentic_qa_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agentic_qa_test')\gexec
