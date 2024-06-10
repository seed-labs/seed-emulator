import * as React from 'react';
import Cookies from 'js-cookie';
import {
   Box,
   Button,
   Typography,
   Stepper,
   Step,
   StepLabel,
   Dialog,
   DialogTitle,
   DialogContent,
   DialogContentText,
   DialogActions,
   CircularProgress,
   Link,
   TextField,
   Paper
} from '@mui/material';
import {
   green
} from '@mui/material/colors'
import { styled } from '@mui/material/styles';
import { useConnectWallet, useWallets } from '@web3-onboard/react';

const steps = [
   'Welcome',
   'Connect to Wallet'
];
// Additional step 'Deploy the Smart Contract' is disabled because we deploy this and get it automatically.

 export function SetupWizard({onFinish}) {
   const [activeStep, setActiveStep] = React.useState(0);
   const [open, setOpen] = React.useState(true);
   const [contractAddress, setContractAddress] = React.useState('');

   const handleClickOpen = () => {
      setOpen(true);
   };

   const handleClose = (event, reason) => {
      if (!['backdropClick', 'escapeKeyDown'].includes(reason)){
         setOpen(false);
      }
   };

   const handleNext = () => {
      if (activeStep >= 0 && activeStep < steps.length) {
         setActiveStep((prevActiveStep) => prevActiveStep + 1);
      }
   };

   const handleBack = () => {
      if (activeStep > 0 && activeStep < steps.length) {
         setActiveStep((prevActiveStep) => prevActiveStep - 1);
      }
   };

   return (
      <Dialog
         open={open}
         onClose={handleClose}
         PaperProps={{
            component: 'form',
            onSubmit: (e) => {
               e.preventDefault();
               handleClose();
               onFinish(contractAddress);
            },
            square: false
         }}
         fullWidth
         maxWidth='md'
      >
         <DialogTitle>
            Setup Wizard
            <Stepper activeStep={activeStep} alternativeLabel sx={{ paddingTop: '1rem' }}>
               {steps.map((label, index) => {
                  const stepProps = {};
                  const labelProps = {};
                  return (
                     <Step key={label} {...stepProps}>
                        <StepLabel {...labelProps}>{label}</StepLabel>
                     </Step>
                  );
               })}
               </Stepper></DialogTitle>
         <DialogContent>
               {activeStep === steps.length ? (
                  <DoneStep />
               ) : (
                  <Box
                     sx={{
                        display: 'flex',
                        flexDirection: 'column',
                        m: 'auto',
                        width: 'fit-content',
                     }}

                  >
                     <StepContent step={activeStep} onAddrChange={(addr) => setContractAddress(addr)}/>
                  </Box>
               )}
         </DialogContent>
         <DialogActions>
            {activeStep === steps.length ? (
               <React.Fragment>
                  <Box sx={{ flex: '1 1 auto' }} />
                  <Button type='submit'>Done</Button>
               </React.Fragment>
            ) : (
               <React.Fragment>
                  <Button
                  disabled={activeStep === 0}
                  onClick={handleBack}
                  >
                  Back
                  </Button>

                  <Box sx={{ flex: '1 1 auto' }} />

                  <Button onClick={handleNext}>
                  {activeStep === steps.length - 1 ? 'Finish' : 'Next'}
                  </Button>
               </React.Fragment>
            )}
         </DialogActions>
      </Dialog>
   );
 }

 function StepContent({step, onAddrChange}) {
   switch (step) {
      case 0:
         return (<WelcomeStep />);
      case 1:
         return (<ConnectWalletStep />);
      case 2:
         return (<ContractStep onChange={onAddrChange}/>);
      default:
         return (
            <React.Fragment>
               <Typography>Step {step + 1}</Typography>
               <DialogContentText>ERROR: This step has not yet been defined.</DialogContentText>
            </React.Fragment>
         );
   }
 }

 function WelcomeStep() {
   return (
      <Box sx={{ display: 'flex', flexDirection: 'column' }}>
         <Typography variant="h4" sx={{ paddingBottom: '1rem' }}>Welcome</Typography>
         <DialogContentText sx={{paddingBottom: '0.5rem'}} >
            This is a distributed application, or dApp, that demonstrates the use of the InterPlanetary
            File System in combination with Ethereum smart contracts. The frontend application handles
            the communication between each of these services, and is written in React with the Material
            UI framework.
         </DialogContentText>
         <DialogContentText sx={{paddingBottom: '0.5rem'}}>
            It looks like this is your first time visiting the SEED Image Board! This setup wizard will
            take you through each step needed to get things up and running. If you are seeing this, but
            are a returning user, go ahead and complete the wizard again.
         </DialogContentText>
      </Box>
   );
 }

 function ConnectWalletStep() {
   const [loading, setLoading] = React.useState(false);
   const [success, setSuccess] = React.useState(false);
   const timer = React.useRef();
   const [{wallet, connecting}, connectWallet, disconnectWallet] = useConnectWallet();

   const buttonSx = {
      ...(success && {
        bgcolor: green[500],
        '&:hover': {
          bgcolor: green[700],
        },
      }),
    };

    React.useEffect(() => {
      return () => {
        clearTimeout(timer.current);
      };
    }, []);
  
    const handleButtonClick = () => {
      if (!loading) {
        setSuccess(false);
        setLoading(true);
        timer.current = setTimeout(() => {
          setSuccess(true);
          setLoading(false);
        }, 2000);
      }
      connectWallet();
    };

   return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Typography variant="h4" sx={{ width:'100%', paddingBottom: '1rem' }}>Ethereum Wallet Setup</Typography>
            <DialogContentText
               sx={{
                  width: '100%',
                  paddingBottom: '0.5rem'
               }}
            >
               In order to use this dApp, you'll need to connect your Ethereum wallet (e.g. Metamask).
               This is used to identify you, as well as to interact with the code on the Ethereum blockchain.
            </DialogContentText>
            <DialogContentText
               sx={{
                  width: '100%',
                  paddingBottom: '0.5rem'
               }}
            >
               Click the button below to get started!
            </DialogContentText>
            <Box sx={{ paddingTop: '2rem', display: 'flex', alignItems: 'center'}}>
               <Box sx={{m: 1, position: 'relative', }}>
                  <Button
                     variant="contained"
                     sx={buttonSx}
                     disabled={connecting || wallet !== null}
                     onClick={handleButtonClick}
                  >
                     {connecting || wallet == null ? 'Connect Wallet' : 'Connected'}
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
            </Box>
         </Box>
   );
 }

 function ContractStep({onChange}) {
   return (
      <Box sx={{ display: 'flex', flexDirection:'column' }}>
         <Typography variant="h4" sx={{ paddingBottom: '1rem' }}>Smart Contract Setup</Typography>
         <DialogContentText sx={{ paddingBottom: '0.5rem' }}>
            At this point, you should have already compiled and deployed the smart contract
            onto the local Ethereum blockchain using <Link 
               href='https://remix.ethereum.org/#lang=en&optimize=true&runs=200&evmVersion=paris&version=soljson-v0.8.25'
               underline='hover'
               target='_blank'
               rel='noopener'>Remix</Link>.
            If you have not done so already, please follow the instructions in the example's
            README file and then return here once you have done so.
         </DialogContentText>
         <DialogContentText sx={{ paddingBottom: '0.5rem' }}>
            The SEED Image Board needs the address of the deployed smart contract so that it can
            communicate with it. This is how this dApp stores the CID for each image file that
            a user uploads.
         </DialogContentText>
         <DialogContentText sx={{ paddingBottom: '0.5rem' }}>
            Please enter the address of the smart contract below.
         </DialogContentText>
         <TextField
            autoFocus
            required
            id='contractAddress'
            name='contractAddress'
            label='Smart Contract Address'
            helperText='Address beginning with 0x...'
            type='text'
            fullWidth
            variant='filled'
            onChange={(e) => onChange(e.target.value)}
         />
      </Box>
   );
 }

 function DoneStep() {
   return (
      <Box sx={{ display: 'flex', flexDirection: 'column' }}>
         <Typography variant="h4">Setup Complete</Typography>
         <DialogContentText sx={{paddingBottom: '0.5rem'}}>
            You have successfully set up the SEED Image Board dApp!
         </DialogContentText>
         <DialogContentText sx={{paddingBottom: '0.5rem'}}>
            Now, you can start adding images which will be reflected based on your current
            Ethereum wallet account each time you visit this page.
         </DialogContentText>
      </Box>
   );
 }

 function WizardError({e}) {
   const timer = React.useRef();
   const [show, setShow] = React.useState(true);

   React.useEffect(() => {
      return () => {
        clearTimeout(timer.current);
      };
    }, []);

   timer.current = setTimeout(() => {
      setShow(false);
   }, 6000);

   return (
      <Box>
         <Paper elevation={5}>
            <Typography variant="h3">Error</Typography>
            <Typography variant='h4'>{e}</Typography>
         </Paper>
      </Box>
   );
 }

 export function WalletConnectPopup() {
   const connectedWallets = useWallets();
   // const [open, setOpen] = React.useState(true);

   // const handleClose = (event, reason) => {
   //    if (!['backdropClick', 'escapeKeyDown'].includes(reason)){
   //       setOpen(false);
   //    }
   // };

   return (
      <Dialog fullWidth maxWidth='md' open={connectedWallets.length > 0}>
         <DialogTitle>Connect a Wallet</DialogTitle>
         <DialogContent><ConnectWalletStep /></DialogContent>
      </Dialog>
   );
 }