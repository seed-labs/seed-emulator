// SPDX-License-Identifier: MIT
pragma solidity ^0.8.15;

contract IPFS_Storage {
    address public owner;
    struct File {
        string cid;
        string name;
    }
    mapping (address => File[]) public files;

    constructor(){
        owner = msg.sender;
    }
    
    function putFile(string calldata hash, string calldata filename) public {
        files[msg.sender].push(File(hash, filename));
    }

    function rmFiles() public {
        delete files[msg.sender];
    }

    function getFiles() public view returns (File[] memory myFiles) {
        return files[msg.sender];
    }
}