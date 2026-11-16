## Table of content

- [Low-level functions in solidity](#solidity)
- [Smart Contract Attacks](#attacks-steps)
- [Reasoning behind the DAO attack](#explanation)

<a name="solidity">
# Low-level functions in solidity

## Terms

- EOA: account holder
- CA: Smart contract

## Low-level functions

When using the solidity programming language, we have access to a couple of functions/apis which let us send ether from one EOA/CA to another or even perform other tasks.
Some of these functions are:
- call
- delegatecall
- transfer

The "call" function can be used for two reasons:
- Sending ether to an EOA or CA
- Calling a function in a certain contract

## Fallback function
As stated in the solidity documentation "The fallback function is executed on a call to the contract if none of the other functions match the given function signature, or if no data was supplied at all and there is no receive Ether function.". This means that calling a non-existing function in a certain contract or sending ether to this contract (given that it does not implement the receive function) will trigger the fallback function.

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


<a name="explanation">
# Reasoning behind the DAO attack

## Error propagation

Error handling and error propagation are some of the main concepts when learning how to code.
When an error is thrown, we either expect the error to be handled and for changed states to revert back to their previous value, or for the code to crash.
Some low-level functions such as "call" fail to propagate errors thrown from deeper functions and return a false value, this is why it is not recommended for solidity developers to use this function.
If not handled properly and in case of an error, we might have scenarios where some variables never reverted back to their original states.

## Reentrancy attack

As mentioned above, using the "call" api triggers the fallback function when sending ether or when calling a non-existing function in a contract (maybe because of a typo).
What an attacker can do is import the vulnerable CA into his malicious CA and add a fallback function in his own CA.
If the vulnerable CA tries to send ether to the malicious contract (when calling a certain function in the vulnerable program), the fallback function in the malicious CA will be triggered.
This means that a CA can potentially run external code without even knowing about it.

## DAO attack

In our Victim CA, the "withdraw" function uses the "call" api to send money to the CA that requests its money back.
The Malicious user takes advantage of that and exploits this by implementing a fallback function in his CA.
The withdraw function will be invoked over and over again from the malicious fallback.
The flow looks like that once the malicious contract withdraws money:
- Malicious calls withdraw -> withdraw function uses "call" to send money to the malicious CA -> fallback function triggered in the malicious CA -> fallback function reinvokes the "withdraw" function -> steps repeated until no ether is left in the contract

## Consequences

The "balances[msg.sender] -= amount" will never be reached.
The attacker will be able to withdraw all the ether in the contract because the check "require(balances[msg.sender] >= amount);" will always succeed.
## Counter-measure

Fixing this issue turns out to be simple. All the owner of the victim contract should do is update the balance of the sender before actually sending ether using the "call" api
This causes the check "require(balances[msg.sender] >= amount);" to fail the next time the Malicious CA tries to invoke the "withdraw" function.

