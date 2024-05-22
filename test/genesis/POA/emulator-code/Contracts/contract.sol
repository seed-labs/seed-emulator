// SPDX-License-Identifier: MIT
//
// https://cryptomarketpool.com/erc20-token-solidity-smart-contract/

pragma solidity ^0.8.0;

interface ERC20 {
    function totalSupply() external pure returns (uint256 _totalSupply);

    function balanceOf(address _owner) external view returns (uint256 balance);

    function transfer(address _to, uint256 _value) external returns (bool success);

    function transferFrom(
        address _from,
        address _to,
        uint256 _value
    ) external returns (bool success);

    function approve(address _spender, uint256 _value) external returns (bool success);

    function allowance(address _owner, address _sender) external view returns (uint256 remaining);

    event Transfer(address indexed _from, address indexed _to, uint256 _value);
    event Approval(address indexed _owner, address indexed _spender, uint256 _value);
}

contract Contract is ERC20 {
    string public constant symbol = "SEED";
    string public constant name = "SEED token";
    uint8 public constant decimals = 18;

    uint256 private constant __totalSupply = 200000000000000000000000;

    mapping(address => uint256) private __balanceOf;

    mapping(address => mapping(address => uint256)) private __allowances;

    constructor() {
        __balanceOf[msg.sender] = __totalSupply;
    }

    function totalSupply() public pure override returns (uint256) {
        return __totalSupply;
    }

    function balanceOf(address _address) public view override returns (uint256) {
        return __balanceOf[_address];
    }

    // Transfer an amount of tokens to another address.
    // Pre-checks:
    //   - The transfer needs to be > 0
    //   - does the msg.sender have enough tokens to forfill the transfer
    // Output:
    //   - decrease the balance of the sender
    //   - increase the balance of the to address
    //   - Emit transfer event
    function transfer(address _to, uint256 _value) public override returns (bool) {
        if (_value > 0 && _value <= balanceOf(msg.sender)) {
            __balanceOf[msg.sender] -= _value;
            __balanceOf[_to] += _value;
            emit Transfer(msg.sender, _to, _value);
            return true;
        }

        return false;
    }

    // this allows someone else (a 3rd party) to transfer from my wallet to someone elses wallet
    // Pre-checks:
    //   - The transfer needs to be > 0
    //   - and the 3rd party has an allowance of > 0
    //   - and the allowance is >= the value of the transfer
    //   - and it is not a contract
    // Output:
    //   - decrease the balance of the from account
    //   - increase the balance of the to account
    //   - Emit transfer event
    function transferFrom(
        address _from,
        address _to,
        uint256 _value
    ) public override returns (bool) {
        if (
            _value > 0 &&
            __allowances[_from][msg.sender] > 0 &&
            __allowances[_from][msg.sender] >= _value &&
            !isContract(_to)
        ) {
            __balanceOf[_from] -= _value;
            __balanceOf[_to] += _value;
            emit Transfer(_from, _to, _value);
            return true;
        }

        return false;
    }

    // This check is to determine if we are sending to a contract?
    // Is there code at this address?  If the code size is greater then 0 then it is a contract.
    function isContract(address _address) public view returns (bool) {
        uint256 codeSize;
        assembly {
            codeSize := extcodesize(_address)
        }

        return codeSize > 0;
    }

    // allows a spender address to spend a specific amount of value
    function approve(address _spender, uint256 _value) external override returns (bool) {
        __allowances[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }

    // shows how much a spender has the approval to spend to a specific address
    function allowance(address _owner, address _spender) external override view returns  (uint256 remaining) {
        return __allowances[_owner][_spender];
    }
}
