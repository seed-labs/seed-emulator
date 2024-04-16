import * as React from 'react';
// import Box from '@mui/material/Box';
// import TextField from '@mui/material/TextField';
// import Grid from '@mui/material/Unstable_Grid2';
// import Button from '@mui/material/Button'
import { 
   FormControl, 
   Stack,
   InputLabel,
   MenuItem,
   Select,
   Box,
   TextField,
   Button
} from '@mui/material';

export function EthControls({onSubmit, acctVar}) {
   const handleAcctChange = async (e) => {
      console.log(e);
   };

   return (
      <Stack spacing={2}>
         {/* Get smart contract address: */}
         <Box
            component="form"
            sx={{
               '& > :not(style)': { m: 1, width: '40ch' },
            }}
            noValidate
            autoComplete="off"
            onSubmit={onSubmit}
         >
            <TextField id="addr" label="Smart Contract Address" variant="filled" />
            <Button variant="outlined" className="btn-eth" type="submit">Submit</Button>
         </Box>
         {/* Choose active account: */}
         {/* <Box sx={{ minWidth: 120 }}>
            <FormControl fullWidth>
            <InputLabel id="acct-label">Account</InputLabel>
            <Select
               labelId="acct-label"
               id="acct"
               value={acctVar}
               label="Account"
               onChange={handleAcctChange}
            >
               <MenuItem value={10}>Ten</MenuItem>
               <MenuItem value={20}>Twenty</MenuItem>
               <MenuItem value={30}>Thirty</MenuItem>
            </Select>
            </FormControl>
         </Box> */}
      </Stack>
   );
}