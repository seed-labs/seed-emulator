import './App.css';
import * as React from 'react';
import { useState } from 'react';
import { Buffer } from 'buffer';
// Custom Imports:
import ImageFilesLayout from './ImageFiles';
import { EthControls } from './EthControls';
import { FileUploadBtn } from './CustomMUI';
import { abi } from './ContractInfo';
// Material UI Imports:
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import Grid from '@mui/material/Unstable_Grid2';
import {
  Typography,
  Stack,
  Paper,
  Container,
  Button
} from '@mui/material';
// IPFS Imports:
import { create } from 'kubo-rpc-client';
// Ethereum Imports:
import { Web3 } from 'web3';

// Connect and setup:
const ipfs = create('http://localhost:5001');
var web3 = null;

function App() {
  const [file, setFile] = useState(null);
  const [urlArr, setUrlArr] = useState([]);
  const [contractAddress, setContractAddress] = useState(null);
  const [connectedAccount, setConnectedAccount] = useState(null);

  // Get ethereum from Metamask:
  async function connectToMetamask() {
    // Check if web3 is available
    if (window.ethereum) {
      // TODO: create popup or step of setup process that says please grant access.

      // Use the browser injected Ethereum provider
      web3 = new Web3(window.ethereum);
      // Request access to the user's MetaMask account (ethereum.enable() is deprecated)
      // Note: Even though, you can also get the accounts from `await web3.eth.getAccounts()`,
      // 	you still need to make a call to any MetaMask RPC to cause MetaMask to ask for consent.
      const ethAccounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      });
      console.log('Assuming account from Metamask: ', ethAccounts[0]);
      setConnectedAccount(ethAccounts[0]);
    } else {
      web3 = new Web3('http://localhost:8545');
      const ethAccounts = await web3.eth.getAccounts();
      console.log('Assuming account from local instance: ', ethAccounts[0])
      setConnectedAccount(ethAccounts[0]);
    }
  };
  
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
    const { cid } = await ipfs.add(file);

    // Create smart contract interface:
    const ipfsStorage = new web3.eth.Contract(abi, contractAddress);
    
    // Save this to account's photos:
    const txReceipt = ipfsStorage.methods.putFile(cid.toString()).send({
      from: connectedAccount,
    });
    console.log(`Saved ${cid} for current account.`);
    console.log(txReceipt);

    const url = `http://localhost:8081/ipfs/${cid}`;
    const img = {
        url: url,
        name: "Test"
    }
    setUrlArr(prev => [...prev, img]);
    } catch (error) {
    console.log(error.message);
    }
    console.log('URLs: ', urlArr);
  };

  const getContract = async (e) => {
    // Prevent page from reloading:
    e.preventDefault();

    // Just test connection:
    console.log('Testing...');
    console.log('Chain ID: ', await web3.eth.getChainId());
    console.log('Last Block: ', await web3.eth.getBlockNumber());
    console.log('Wallet Balance: ', await web3.eth.getBalance('0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'));

    // Get form data:
    const address = e.target.elements.addr.value;
    setContractAddress(address);
    
    // Create smart contract interface:
    const ipfsStorage = new web3.eth.Contract(abi, address);
    console.log(ipfsStorage.options);

    // Populate with user's images, if they have any:
    var myCIDs = await ipfsStorage.methods.getFiles().call({
      from: connectedAccount,
    });
    console.log('From contract: ', myCIDs);
    const myUrls = myCIDs.map((cid) => { return { url: `http://localhost:8081/ipfs/${cid}`, name: "Test" } } );
    console.log('URLs: ', myUrls);
    setUrlArr(myUrls);
  }

  return (
    <div className="App">
      <Stack spacing={2}>
        <Button onClick={connectToMetamask}>Connect Metamask</Button>
        <EthControls onSubmit={getContract} acctVar={connectedAccount} />
        <Paper sx={{ padding: '1rem', margin:'3rem'}}>
          <Typography variant="h4">Upload</Typography>
          <form className="form" onSubmit={handleSubmit}>
            <Grid container spacing={2}>
              <Grid xs display="flex" justifyContent="center" alignItems="center">
                  <FileUploadBtn onChange={retrieveFile} className="io-file" />
              </Grid>
              <Grid xs display="flex" justifyContent="center" alignItems="center">
                <Button variant="outlined" type="submit" className="btn-submit">Submit</Button>
              </Grid>
            </Grid>
          </form>
        </Paper>
      </Stack>
      <Container maxWidth="false" className="display">
        {urlArr.length !== 0
          ? <ImageFilesLayout itemData={urlArr} />
          : <Typography variant="h5">No Photos Found</Typography>}
      </Container>
    </div>
  );
}

export default App;
