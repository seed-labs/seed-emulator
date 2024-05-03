import './App.css';
import * as React from 'react';
import { useState } from 'react';
import { Buffer } from 'buffer';
import Cookies from 'js-cookie';
// Custom Imports:
import ImageBoard from './ImageFiles';
import { SetupWizard, WalletConnectPopup } from './SetupWizard';
import {
  ErrorPopup
} from './CustomMUI';
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
  Box
} from '@mui/material';
// Web-3 Onboard Imports:
import {
  Web3OnboardProvider,
  init,
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
  rpcUrl: 'http://localhost:8545',
  icon: 'SEEDfavicon.ico',
  color: '#2471A3'
}
const wallets = [injectedModule()]
const chains = [SEEDchain]
const web3Onboard = init({
  wallets,
  chains,
  appMetadata: {
    name: 'SEED Image Board',
    logo: '/internet-emulator-s.jpg',
    icon: '/favicon.ico',
    description: 'A demo image board dApp built with Ethereum smart contracts and the InterPlanetary File System.'
  },
  connect: {
    autoConnectLastWallet: true
  },
  theme: 'dark'
})
var web3 = null;
const ipfs = create('http://localhost:5001');

function ImageBoardApp({ pageProps }) {
  // Store in cookie: onboarded
  const appCookies = ['onboarded'];
  // imgArr = [{name: 'filename.png', cid: 'CIDasAString', url: 'http://localhost:8081/dsajfhasjdfkald'}]
  const [imgArr, setImgArr] = useState([]);
  const [{wallet, connecting}, connectWallet, disconnectWallet] = useConnectWallet();
  const [wizardComplete, setWizardComplete] = useState(false);
  const [connectedAccount, setConnectedAccount] = useState(null);
  // File: {name: 'name', data: Buffer}
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [contractAddress, setContractAddress] = useState(null);

  function resetDapp(e) {
    try{
      appCookies.map((value) => Cookies.remove(value));
      window.location.reload();
    } catch (err) {
      setError(err);
    }
  }
  
  function handleWizardFinish(contractAddr) {
    setWizardComplete(true);
    Cookies.set('onboarded', true);
    // Uncomment the below and re-enable the contract step in the SetupWizard to add this manually.
    // setContractAddress(contractAddr);
    handleConnect();
  }

  function handleConnect() {
    try {
      web3 = new Web3(window.ethereum);
      setConnectedAccount(wallet?.accounts[0].address);
    } catch (err) {
      setError(err);
    }
  }

  const retrieveFile = (e) => {
    const data = e.target.files[0];
    const reader = new window.FileReader()
    try {
      reader.readAsArrayBuffer(data)
      reader.onloadend = () => {
        setFile({
          name: data.name,
          data: Buffer(reader.result)
          });
      }
      console.log('Read file ', data.name);
    } catch (err) {
      setError(err);
    }
    
    e.preventDefault();
  };

  const storeFile = async (e) => {
    e.preventDefault();
    console.log('Submitting...');
    try {
    const { cid } = await ipfs.add(file.data);
    console.log('Added to IPFS')

    // Create smart contract interface:
    const ipfsStorage = new web3.eth.Contract(abi, contractAddress);
    
    // Save this to account's photos:
    const txReceipt = ipfsStorage.methods.putFile(cid.toString(), file.name).send({
      from: connectedAccount,
    });
    console.log(`Saved ${cid} for current account.`);
    console.log(txReceipt);

    const url = `http://localhost:8081/ipfs/${cid}`;
    const img = {
      cid: cid.toString(),
      url: url,
      name: file.name
    }
    setImgArr(prev => [...prev, img]);
    } catch (err) {
      setError(err);
    }
  };

  async function getStoredImages() {
    try {
    // Create smart contract interface:
    const ipfsStorage = new web3.eth.Contract(abi, contractAddress);

    // Populate with user's images, if they have any:
    var myCIDs = await ipfsStorage.methods.getFiles().call({
      from: connectedAccount,
    });
    console.log('From contract: ', myCIDs);
    const myUrls = myCIDs.map((file) => { return { cid: file.cid, url: `http://localhost:8081/ipfs/${file.cid}`, name: file.name } } );
    setImgArr(myUrls);
  } catch (err) {
    setError(err);
  }
  }

  // DEBUGGING:
  React.useEffect(() => {
    console.log('Images: ', imgArr);
  }, [imgArr]);
  React.useEffect(() => {
    console.log('Connected Account: ', connectedAccount);
  }, [connectedAccount]);
  React.useEffect(() => {
    console.log('Contract Address: ', contractAddress);
  }, [contractAddress]);

  // Get new images if user changes:
  // React.useEffect(() => {
  //   if (connectedAccount !== null || connectedAccount !== undefined) {
  //     window.location.reload();
  //   }
  // }, [connectedAccount]);

  // Get the deployed smart contract's address:
  React.useEffect(() => {
    const fetchData = async () => {
      const response = await fetch('/contract_address.txt');
      const rData = await response.text();
      setContractAddress(rData);
    };
    fetchData();
  }, []);

  React.useEffect(() => {
    // If web3 isn't connected to the provider, but we've already onboarded
    // just connect:
    if (!web3 && Cookies.get('onboarded')){
      handleConnect();
    }

    // If there is a connected wallet but no account, update that:
    if (wallet && !connectedAccount){
      setConnectedAccount(wallet?.accounts[0].address);
    }

    // If we have the contract, account, web3, and ipfs, get the user's images:
    if (contractAddress && connectedAccount && web3 && ipfs) {
      getStoredImages();
    }
  }, [wallet, connectedAccount]);

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
          {error
            ? <ErrorPopup msg={error.message} onAttemptFix={resetDapp} onClose={() => setError(null)}/>
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
