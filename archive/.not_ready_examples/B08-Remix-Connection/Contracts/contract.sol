pragma solidity ^0.8.0;

contract Crowdfunding {
    uint256 amount;

    receive() external payable {
        amount += msg.value;
    }

    function claimFunds(address payable _to, uint _amount) public payable {
        _to.transfer(_amount);
    }
}