import * as React from 'react';

import ImageList from '@mui/material/ImageList';
import ImageListItem from '@mui/material/ImageListItem';
import ImageListItemBar from '@mui/material/ImageListItemBar';
import ListSubheader from '@mui/material/ListSubheader';
import { Typography } from '@mui/material';


export default function ImageFilesLayout({itemData}) {
   return (
     <ImageList>
       <ImageListItem key="Subheader" cols={2} sx={{ mb: 3 }}>
         <ListSubheader component="div"><Typography variant="h4">Uploaded Images</Typography></ListSubheader>
       </ImageListItem>
       {itemData.map((item) => (
         <ImageListItem key={item.url}>
           <img
             srcSet={`${item.url}?w=248&fit=crop&auto=format&dpr=2 2x`}
             src={`${item.url}?w=248&fit=crop&auto=format`}
             alt={item.name}
             loading="lazy"
           />
           <ImageListItemBar
             title={item.name}
            //  subtitle={item.author}
            //  actionIcon={
            //    <IconButton
            //      sx={{ color: 'rgba(255, 255, 255, 0.54)' }}
            //      aria-label={`info about ${item.name}`}
            //    >
            //      <InfoIcon />
            //    </IconButton>
            //  }
           />
         </ImageListItem>
       ))}
     </ImageList>
   );
 }