import React, { useState } from 'react';
import { styled, useTheme } from '@mui/material/styles';
import Button from '@mui/material/Button';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Box,
  CircularProgress,
  Typography
} from '@mui/material';
import {
  green
} from '@mui/material/colors';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import CloudUploadIcon from '@mui/icons-material/CloudUpload';


export const VisuallyHiddenInput = styled('input')({
   clip: 'rect(0 0 0 0)',
   clipPath: 'inset(50%)',
   height: 1,
   overflow: 'hidden',
   position: 'absolute',
   bottom: 0,
   left: 0,
   whiteSpace: 'nowrap',
   width: 1,
 });

 export function FileUploadBtn({onChange, className, disabled}){
  const [btnLabel, setBtnLabel] = useState('Upload File');

  const handleChange = (e) => {
    setBtnLabel(e.target.files[0].name);
    onChange(e);
  };

  React.useEffect(() => {
    if (!disabled && btnLabel !== 'Upload File'){
      setBtnLabel('Upload File');
    }
  }, [disabled]);

  return (
    <Button
      component="label"
      role={undefined}
      variant="outlined"
      tabIndex={-1}
      startIcon={<CloudUploadIcon />}
      className="btn-upload"
      disabled={disabled}
    >
      {btnLabel}
      <VisuallyHiddenInput 
        type="file"
        accept="image/*"
        name="data"
        id="file-upload"
        onChange={handleChange}
        className={className}
      />
    </Button>
  );
 };

 export function LoadingButton({children, loading, success, onClick, ...buttonProps}) {
  const buttonSx = {
    ...(success && {
      bgcolor: green[500],
      '&:hover': {
        bgcolor: green[700],
      },
    }),
  };

  const handleButtonClick = async (e) => {
    onClick(e);
  };

  return (
    <Box sx={{m: 1, position: 'relative', }}>
      <Button
        variant="contained"
        sx={buttonSx}
        disabled={loading}
        onClick={handleButtonClick}
        {...buttonProps}
      >
        {children}
      </Button>
      {loading && (
        <CircularProgress
          size={24}
          sx={{
          color: green[500],
          position: 'absolute',
          top: '50%',
          left: '50%',
          marginTop: '-12px',
          marginLeft: '-12px',
          }}
        />
      )}
    </Box>
  );
 }

 export function ErrorPopup({msg, onAttemptFix, onClose}) {
  const [open, setOpen] = useState(true);
  const theme = useTheme();

  const handleFix = (e) => {
    if (onAttemptFix) {
      onAttemptFix(e);
    }
    setOpen(false);
  };

  const handleClose = (e) => {
    setOpen(false);
    if (onClose) {
      onClose(e);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      maxWidth='md'
      PaperProps={{
        sx: {
          padding: '1rem'
        }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '0.5rem'}}>
        <ErrorOutlineIcon fontSize='large' sx={{ color: theme.palette.error.main }}/>
        <Typography variant='h5'>Server Error</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ paddingBottom: '0.5rem' }}>A server side error has occurred.</DialogContentText>
        <DialogContentText>{msg}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleFix} variant='outlined'>Attempt Fix</Button>
        <Box sx={{ flex: '1 1 auto' }} />
        <Button onClick={handleClose} variant='outlined' color='error'>Close</Button>
      </DialogActions>
    </Dialog>
  );
 }