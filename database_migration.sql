-- Migration: Add chat_id to employee table and create leave_requests table
-- Date: 2025
-- Description: Enables supervisor approval workflow with Google Chat cards

-- Step 1: Add chat_id column to employee table (if it doesn't exist)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employee' 
        AND column_name = 'chat_id'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.employee ADD COLUMN chat_id VARCHAR(255);
    END IF;
END $$;

-- Step 2: Create leave_requests table (if it doesn't exist)
CREATE TABLE IF NOT EXISTS public.leave_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,
    employee_email VARCHAR(255) NOT NULL,
    supervisor_email VARCHAR(255) NOT NULL,
    leave_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    employee_space VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    decision_note TEXT
);

-- Step 3: Create index on request_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_leave_requests_request_id ON public.leave_requests(request_id);

-- Step 4: Create index on employee_email and status for querying
CREATE INDEX IF NOT EXISTS idx_leave_requests_employee ON public.leave_requests(employee_email, status);

-- Step 5: Create index on supervisor_email and status for supervisor queries
CREATE INDEX IF NOT EXISTS idx_leave_requests_supervisor ON public.leave_requests(supervisor_email, status);

-- Optional: Add comments to explain the schema
COMMENT ON TABLE public.leave_requests IS 'Stores employee leave requests and their approval status';
COMMENT ON COLUMN public.leave_requests.request_id IS 'Unique identifier for the leave request';
COMMENT ON COLUMN public.leave_requests.status IS 'Request status: PENDING, APPROVED, DECLINED, CANCELLED';
COMMENT ON COLUMN public.employee.chat_id IS 'Google Chat space ID for the employee';

