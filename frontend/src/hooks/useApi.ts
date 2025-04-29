import { useState, useCallback } from 'react';
import { findSingleEmail, findBatchEmails, checkHealth } from '../services/api';
import {
    SingleContactRequest,
    BatchContactRequest,
    ProcessingResult,
} from '../types';

// Define a generic structure for the hook's return value
interface UseApiState<T> {
    data: T | null;
    isLoading: boolean;
    error: Error | null;
}

// --- Hook for Single Email Lookup ---
export const useFindSingleEmail = () => {
    const [state, setState] = useState<UseApiState<ProcessingResult>>({
        data: null,
        isLoading: false,
        error: null,
    });

    const execute = useCallback(async (contact: SingleContactRequest) => {
        setState({ data: null, isLoading: true, error: null });
        try {
            const result = await findSingleEmail(contact);
            setState({ data: result, isLoading: false, error: null });
            return result; // Return result for potential chaining or immediate use
        } catch (err) {
            const error = err instanceof Error ? err : new Error('An unknown error occurred');
            setState({ data: null, isLoading: false, error: error });
            throw error; // Re-throw error so the component can catch it if needed
        }
    }, []); // No dependencies, findSingleEmail is stable

    return { ...state, execute };
};


// --- Hook for Batch Email Lookup ---
export const useFindBatchEmails = () => {
    const [state, setState] = useState<UseApiState<ProcessingResult[]>>({
        data: null,
        isLoading: false,
        error: null,
    });

    const execute = useCallback(async (batchRequest: BatchContactRequest) => {
        setState({ data: null, isLoading: true, error: null });
        try {
            const results = await findBatchEmails(batchRequest);
            setState({ data: results, isLoading: false, error: null });
            return results;
        } catch (err) {
            const error = err instanceof Error ? err : new Error('An unknown error occurred');
            setState({ data: null, isLoading: false, error: error });
            throw error;
        }
    }, []); // No dependencies, findBatchEmails is stable

    return { ...state, execute };
};


// --- Hook for Health Check ---
interface HealthStatus { status: string };

export const useCheckHealth = () => {
     const [state, setState] = useState<UseApiState<HealthStatus>>({
        data: null,
        isLoading: false,
        error: null,
    });

     const execute = useCallback(async () => {
        setState({ data: null, isLoading: true, error: null });
        try {
            const result = await checkHealth();
            setState({ data: result, isLoading: false, error: null });
            return result;
        } catch (err) {
             const error = err instanceof Error ? err : new Error('Failed to check API health');
             setState({ data: null, isLoading: false, error: error });
             throw error;
        }
    }, []); // No dependencies, checkHealth is stable

    return { ...state, execute };
}; 