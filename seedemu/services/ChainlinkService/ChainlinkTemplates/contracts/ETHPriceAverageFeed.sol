// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract ETHPriceAverageFeed is ChainlinkClient, Ownable {
    using Chainlink for Chainlink.Request;

    uint256 private constant ORACLE_PAYMENT = 1360000000000000000;
    uint256 public averagePrice;
    uint256 public responsesCount;
    address public linkToken;

    struct OracleData {
        address oracle;
        bytes32 jobId;
        bool isActive;
        uint256 price;
    }

    OracleData[] public oracles;
    mapping(bytes32 => bool) private pendingRequests;
    
    constructor() Ownable(msg.sender){}

    function setLinkToken(address _link_token) public onlyOwner{
        setChainlinkToken(_link_token);  
        linkToken = _link_token;  
    }

    function addOracle(address _oracle, string memory _jobId) public onlyOwner {
        bytes32 jobIdBytes = stringToBytes32(_jobId);
        oracles.push(OracleData({
            oracle: _oracle,
            jobId: jobIdBytes,
            isActive: true,
            price: 0
        }));
    }

    function addOracles(address[] memory _oracles, string memory _jobId) public onlyOwner {
        bytes32 jobIdBytes = stringToBytes32(_jobId);
        for (uint256 i = 0; i < _oracles.length; i++) {
            oracles.push(OracleData({
                oracle: _oracles[i],
                jobId: jobIdBytes,
                isActive: true,
                price: 0
            }));
        }
    }

    function deactivateOracle(uint256 _index) public onlyOwner {
        require(_index < oracles.length, "Invalid oracle index");
        oracles[_index].isActive = false;
    }

    function requestETHPriceData(string memory url, string memory path) public {
        for (uint256 i = 0; i < oracles.length; i++) {
            if (oracles[i].isActive) {
                Chainlink.Request memory request = buildChainlinkRequest(
                    oracles[i].jobId,
                    address(this),
                    this.fulfill.selector
                );

                request.add("get", url);
                request.add("path", path);
                request.addInt("multiply", 100);

                bytes32 requestId = sendChainlinkRequestTo(oracles[i].oracle, request, ORACLE_PAYMENT);
                pendingRequests[requestId] = true;
            }
        }
    }

    function fulfill(bytes32 _requestId, uint256 _price) public recordChainlinkFulfillment(_requestId) {
        require(pendingRequests[_requestId], "Request is not valid");
        pendingRequests[_requestId] = false;

        uint256 sumPrices = 0;
        uint256 activeOracles = 0;

        for (uint256 i = 0; i < oracles.length; i++) {
            if (oracles[i].oracle == msg.sender && oracles[i].isActive) {
                oracles[i].price = _price;
                break;
            }
        }

        for (uint256 i = 0; i < oracles.length; i++) {
            if (oracles[i].isActive && oracles[i].price > 0) {
                sumPrices += oracles[i].price;
                activeOracles++;
            }
        }

        if (activeOracles > 0) {
            averagePrice = sumPrices / activeOracles;
            responsesCount = activeOracles;
        }
    }

    function getResponsesCount() public view returns (uint256) {
        return responsesCount;
    }

    function stringToBytes32(string memory source) private pure returns (bytes32 result) {
        bytes memory tempEmptyStringTest = bytes(source);
        if (tempEmptyStringTest.length == 0) {
            return 0x0;
        }
        assembly {
            result := mload(add(source, 32))
        }
    }

    receive() external payable {}
}
