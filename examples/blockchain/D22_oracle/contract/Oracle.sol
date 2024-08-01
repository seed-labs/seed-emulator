// SPDX-License-Identifier: MIT
pragma solidity >=0.8.12 <0.8.19;

contract Oracle {
    address public owner;
    uint256 price;

    constructor(){
        owner = msg.sender;
	price = 0;
    }

    receive() external payable {  }


    function getPrice() public view returns (uint) {
        return price;
    }

    event UpdatePriceMessage(address indexed _from);

    function updatePrice() public payable {
        emit UpdatePriceMessage(msg.sender);
    }

    function setPrice(uint p) public {
        price = p;
    }
}
