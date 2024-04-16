import { useState } from 'react';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Unstable_Grid2';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ImageFilesLayout from './ImageFiles';
import Container from '@mui/material/Container';
import { CardMedia, Typography } from '@mui/material';
import { VisuallyHiddenInput } from './CustomMUI';


export function IpfsControls({client}) {
   const [file, setFile] = useState(null);
   const [urlArr, setUrlArr] = useState([]);
   
   const retrieveFile = (e) => {
      const data = e.target.files[0];
      const reader = new window.FileReader()
      reader.readAsArrayBuffer(data)
      reader.onloadend = () => {
      setFile(Buffer(reader.result));
      }
      console.log('Read file ', data.name);
      e.preventDefault();
   };

   const handleSubmit = async (e) => {
      e.preventDefault();
      console.log('Submitting...');
      try {
      const { cid } = await client.add(file);
      const url = `http://localhost:8081/ipfs/${cid}`;
      const img = {
         url: url,
         name: "Test"
      }
      setUrlArr(prev => [...prev, img]);
      } catch (error) {
      console.log(error.message);
      }
   };

   return (
      <form className="form" onSubmit={handleSubmit}>
          {/* <input type="file" name="data" onChange={retrieveFile} /> */}
          <Grid container spacing={2}>
            <Grid xs display="flex" justifyContent="center" alignItems="center">
              <Button
                component="label"
                role={undefined}
                variant="outlined"
                tabIndex={-1}
                startIcon={<CloudUploadIcon />}
                className="btn-upload"
              >
                Upload File
                <VisuallyHiddenInput type="file" name="data" onChange={retrieveFile} className="io-file" />
              </Button>
            </Grid>
            <Grid xs display="flex" justifyContent="center" alignItems="center">
              <Button variant="outlined" type="submit" className="btn-submit">Submit</Button>
            </Grid>
          </Grid>
        </form>
   );
};

export function ImageWall() {
   return (
      <Container maxWidth="false" className="display">
        {urlArr.length !== 0
          ? <ImageFilesLayout itemData={urlArr} />
          : <Typography variant="h4">Upload Data</Typography>}
      </Container>
   );
}