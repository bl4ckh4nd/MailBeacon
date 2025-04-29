import React from 'react';
import { Box, CircularProgress } from '@mui/material';

interface LoadingSpinnerProps {
  size?: number | string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 40 }) => {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 3 }}>
      <CircularProgress size={size} />
    </Box>
  );
};

export default LoadingSpinner; 