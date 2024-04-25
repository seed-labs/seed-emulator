import * as React from 'react';
import {
  Typography,
  ImageList,
  ImageListItem,
  ImageListItemBar,
  ListSubheader,
  Box,
  FormControl,
  Paper,
  Button,
  useTheme
} from '@mui/material';
import {
  green
} from '@mui/material/colors';
import {
  FileUploadBtn
} from './CustomMUI';

export default function ImageBoard({itemData, onUpload, onSubmit}) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column' }}>
      <FileUploadSection onUpload={onUpload} onSubmit={onSubmit}/>
      {itemData.length !== null
        ? <ImageFilesLayout itemData={itemData} />
        : <Typography variant="h5">No Photos Found</Typography>}
    </Box>
  );
}

function ImageFilesLayout({itemData}) {
  const numCols = 3;
    return (
        <ImageList cols={numCols}>
          <ImageListItem key="Subheader" cols={numCols} sx={{ mb: 3 }}>
            <ListSubheader component="div"><Typography variant="h5">Uploaded Images</Typography></ListSubheader>
          </ImageListItem>
          {itemData.map((item) => (
            <IPFSImageItem item={item} />
          ))}
        </ImageList>
   );
 }

 function FileUploadSection({onUpload, onSubmit}) {
  const [uploaded, setUploaded] = React.useState(false);
  const buttonSx = {
    ...(uploaded && {
      bgcolor: green[500],
      '&:hover': {
        bgcolor: green[700],
      },
    }),
  };

  const handleUpload = (e) => {
    setUploaded(true);
    onUpload(e);
  };

  const handleSubmit = (e) => {
    setUploaded(false);
    onSubmit(e);
  }

  return (
    <Paper
      elevation={3}
      component='form'
      onSubmit={handleSubmit}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        p: '3rem',
        width: '80vw',
        m: 'auto'
      }}
    >
      <Typography variant='h4' sx={{ paddingBottom: '1rem' }}>Upload</Typography>
      <Typography variant='p' sx={{ paddingBottom: '1rem' }}>
        Click the "Upload" button to choose a file to upload. This file must be an image file.
        Once you have uploaded the file, you may add it to your personal image board.
      </Typography>
      <FormControl sx={{ display: 'flex', flexDirection: 'row', alignItems: 'center' , gap: '1rem'}}>
        <FileUploadBtn onChange={handleUpload} disabled={uploaded}/>
        <Button variant='outlined' type='submit' disabled={!uploaded}>Add to Board</Button>
      </FormControl>
    </Paper>
  );
 }

 function IPFSImageItem({item}) {
  const theme = useTheme();
  const cidSubtitle = (<Typography variant='caption' sx={{color: theme.palette.text.secondary}}>{item.cid}</Typography>);

  return (
    <ImageListItem key={item.cid}>
      <img
        srcSet={`${item.url}?w=248&fit=crop&auto=format&dpr=2 2x`}
        src={`${item.url}?w=248&fit=crop&auto=format`}
        alt={item.name}
        loading="lazy"
        style={{ borderRadius: '0.5rem' }}
      />
      <ImageListItemBar
          title={item.name}
          subtitle={cidSubtitle}
          sx={{
            borderBottomLeftRadius: '0.5rem',
            borderBottomRightRadius: '0.5rem',
          }}
        />
    </ImageListItem>
  );
 }