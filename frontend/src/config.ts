// Read API base URL from environment variables (VITE_ prefix is important for Vite)
// See: https://vitejs.dev/guide/env-and-mode.html
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1'; // Matches backend API router prefix

export const config = {
  api: {
    baseUrl: API_BASE_URL,
    prefix: API_PREFIX,
    endpoints: {
      single: `${API_BASE_URL}${API_PREFIX}/find-single`,
      batch: `${API_BASE_URL}${API_PREFIX}/find-batch`,
      health: `${API_BASE_URL}${API_PREFIX}/health`,
    },
  },
  // Add other frontend specific settings here if needed
  // e.g., defaultTimeout: 30000,
};

// Optional: Log the config in development mode for easier debugging
if (import.meta.env.DEV) {
  console.log('Frontend Config:', config);
}
