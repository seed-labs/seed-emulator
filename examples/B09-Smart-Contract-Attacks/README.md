## Table of content

- [Smart Contract Attacks](#attacks-steps)

<a name="attacks-steps">
# Smart Contract Attacks

## Prerequisits

Connecting to Remix IDE (check example B08-Remix-Connection)

## About Remix
Remix has 5 main sections in its sidebar:
- File explorer
- Solidity compiler
- Deploy and run transactions
- Debugger
- Plugin manager

We are interested in the first 3
In the first section, File explorer, you can create your smart contracts inside the contracts folder.
In the second section, Solidity compiler, you can select the solidity compiler of your choice depending on what version you are using in your code.
In the third section, Deploy and run transactions, you can connect to the network of your choice, deploy smart contracts, and interact with them.

## Creating your smart contracts

This part is related to section 1 of the Remix IDE.
  
Navigate to the "File explorer" section.
  
Find the "contracts" folder.
  
Right click on the folder and select "New File".
  
Go to examples/B09-Smart-Contract-Attacks/Contracts.
  
Copy/Paste the contracts you need (e.g., DaoVictim.sol, DaoMalicious.sol).
  
Make sure the new files you created in Remix match the name of the contracts.

## Compiling your smart contracts

This part is related to section 2 of the Remix IDE.

Go to the "Solidity Compiler" section.
Select the appropriate compiler version from the "Compiler" dropdown.

Option 1: Save the file, this should automatically compile the contracts.
  
Option 2: Click on Compile button.

## Deploying your smart contracts

This part is related to section 3 of the Remix IDE.

We will show how to deploy the DAO smart contracts from Remix.
Step 1: Change "wei" to "ether".

Step 2: Select the DaoVictim contract under "contract". If it does not appear there, go back to your code, save it, and check again.

Step 3: Click on "Deploy". You will see a successful transaction in the console and an instance of your smart contract under "Deployed Contracts".

Step 4: Change the "Value" integer from 0 to 2 and click on the "deposit" function in your deployed smart contract. You cannot deposit more ether than what your account has. You will see a successful transaction in the console. Clicking on "getBalance" will show the total balance of the smart contract which is now 2 ether.

Step 5: Change account from the "Account" dropdown and repeat step 4 above. "getBalance" will show 4 ether now.

Step 6: Select a third account from the "Account" list. This will be our malicious user.

Step 7: Select the DaoMalicious contract from under the "Contract" list. If it does not appear there, go back to your code, save it, and check again.

Step 8: This smart contracts takes the address of DaoVictim as parameter. It needs to be filled next to the "Deploy" button. You can find the victim's address by copying it from under the "Deployed Contracts". Enter the parameter and click on "Deploy".
You will now see a new entry under the "Deployed Contracts".

## Dao Attack

Step 1: Change the "Value" integer from 0 to 1 and click on the "attack" function in your malicious smart contract. Click on the "getBalance" function in the vicim contract, it shows 0 ether! Click on the "getBalance" function in the malicious contract, it shows 5 ether!

Step 2: The stolen money is now in the malicious contract and not in the malicious user's account. Click on the "cashOut" function and check the amount of ether the malicious account has under the "Account" list.
