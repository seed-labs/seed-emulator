// SPDX-License-Identifier: MIT
pragma solidity ^0.8.15;

contract IPFS_Storage {
    address public owner;
    // Mapping of owner -> [cid]:
    mapping (address => string[]) public files;

    constructor(){
        owner = msg.sender;
    }
    
    function putFile(string calldata hash) public {
        files[msg.sender].push(hash);
    }

    function rmFiles() public {
        delete files[msg.sender];
    }

    function getFiles() public view returns (string[] memory myFiles) {
        return files[msg.sender];
    }
}