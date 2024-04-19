import './App.css';
import * as React from 'react';
import { useState } from 'react';
import { Buffer } from 'buffer';
import Cookies from 'js-cookie';
import logo from './logo.svg';
// Custom Imports:
import ImageBoard from './ImageFiles';
import { SetupWizard, WalletConnectPopup } from './SetupWizard';
import { FileUploadBtn } from './CustomMUI';
import { abi } from './ContractInfo';
// Material UI Imports:
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import {
  createTheme,
  ThemeProvider,
  CssBaseline,
  Box,
  Typography,
  Fab
} from '@mui/material';
import AccountBalanceWalletOutlined from '@mui/icons-material/AccountBalanceWalletOutlined';
// Web-3 Onboard Imports:
import {
  Web3OnboardProvider,
  init,
  useWallets,
  useConnectWallet
} from '@web3-onboard/react';
import injectedModule from '@web3-onboard/injected-wallets';
// Web3 Imports:
import { Web3 } from 'web3';
// IPFS Imports:
import { create } from 'kubo-rpc-client';

const darkTheme = createTheme({ palette: { mode: 'dark' } });

const SEEDchain = {
  id: 1337,
  token: 'ETH',
  label: 'SEED Emulator Blockchain',
  rpcUrl: 'http://localhost:8545'
}
const wallets = [injectedModule()]
const chains = [SEEDchain]
const web3Onboard = init({
  wallets,
  chains,
  appMetadata: {
    name: 'SEED Image Board',
    logo: logo,
    description: 'A demo of a dApp built with Ethereum smart contracts and the InterPlanetary File System.'
  },
  connect: {
    autoConnectLastWallet: true
  }
})
var web3 = null;
const ipfs = create('http://localhost:5001');

function ImageBoardApp({ pageProps }) {
  // Store in cookie: contractAddress, onboarded
  // imgArr = [{name: 'filename.png', cid: 'CIDasAString', url: 'http://localhost:8081/dsajfhasjdfkald'}]
  const [imgArr, setImgArr] = useState([]);
  const [{wallet, connecting}, connectWallet, disconnectWallet] = useConnectWallet();
  const [wizardComplete, setWizardComplete] = useState(false);
  const [connectedAccount, setConnectedAccount] = useState(null);
  const [file, setFile] = useState(null);
  
  function handleWizardFinish(contractAddr) {
    setWizardComplete(true);
    Cookies.set('onboarded', true);
    Cookies.set('contractAddress', contractAddr);
    handleConnect();
  }

  function handleConnect() {
    web3 = new Web3(window.ethereum);
    web3.eth.getChainId().then(console.log);
    console.log(web3Onboard.state.get());
    setConnectedAccount(wallet?.accounts[0].address);
  }

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

  const storeFile = async (e) => {
    e.preventDefault();
    console.log('Submitting...');
    try {
    const { cid } = await ipfs.add(file);

    // Create smart contract interface:
    const ipfsStorage = new web3.eth.Contract(abi, Cookies.get('contractAddress'));
    
    // Save this to account's photos:
    const txReceipt = ipfsStorage.methods.putFile(cid.toString()).send({
      from: connectedAccount,
    });
    console.log(`Saved ${cid} for current account.`);
    console.log(txReceipt);

    const url = `http://localhost:8081/ipfs/${cid}`;
    const img = {
      cid: cid.toString(),
      url: url,
      name: "Test"
    }
    setImgArr(prev => [...prev, img]);
    } catch (error) {
    console.log(error.message);
    }
    console.log('URLs: ', imgArr);
  };

  async function getStoredImages() {
    // Create smart contract interface:
    const ipfsStorage = new web3.eth.Contract(abi, Cookies.get('contractAddress'));
    console.log(ipfsStorage.options);

    // Populate with user's images, if they have any:
    var myCIDs = await ipfsStorage.methods.getFiles().call({
      from: connectedAccount,
    });
    console.log('From contract: ', myCIDs);
    const myUrls = myCIDs.map((cid) => { return { cid: cid.toString(), url: `http://localhost:8081/ipfs/${cid}`, name: "Test" } } );
    console.log('URLs: ', myUrls);
    setImgArr(myUrls);
  }

  React.useEffect(() => {
    if (!web3 && Cookies.get('onboarded')){
      handleConnect();
      getStoredImages();
    }

    if (wallet && !connectedAccount){
      setConnectedAccount(wallet?.accounts[0].address);
      getStoredImages();
    }

    if (Cookies.get('contractAddress') && connectedAccount && web3) {
      getStoredImages();
    }
  }, [wallet, web3, connectedAccount]);

  // React.useEffect(() => {
  //   console.log('Onboarded: ', Cookies.get('onboarded'));
  //   console.log('Contract Address: ', Cookies.get('contractAddress'));
  //   console.log(web3Onboard.state.get());
  // });

  return (
      <ThemeProvider theme={darkTheme}>
        <CssBaseline />
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center'
          }}
        >
          {Cookies.get('onboarded') || wizardComplete
            ? <ImageBoard itemData={imgArr} onUpload={retrieveFile} onSubmit={storeFile}/>
            : <SetupWizard onFinish={handleWizardFinish} {...pageProps} />
          }
          {!wallet && Cookies.get('onboarded')
            ? <WalletConnectPopup />
            : <React.Fragment></React.Fragment>
          }
        </Box>
      </ThemeProvider>
  );
}

function App({pageProps}) {
  return (
    <div className="App">
      <Web3OnboardProvider web3Onboard={web3Onboard}>
        <ImageBoardApp {...pageProps}/>
      </Web3OnboardProvider>
    </div>
  );
}

export default App;
