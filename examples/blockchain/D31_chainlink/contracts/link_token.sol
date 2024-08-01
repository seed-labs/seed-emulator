pragma solidity ^0.4.11;


import './ERC677Token.sol';
import './token/linkStandardToken.sol';


contract LinkToken is linkStandardToken, ERC677Token {

  uint public constant totalSupply = 10**27;
  string public constant name = 'ChainLink Token';
  uint8 public constant decimals = 18;
  string public constant symbol = 'LINK';
  uint public constant creatorInitialBalance = 1000 * (10 ** uint(decimals));
  uint public poolBalance;
  uint public constant tokenDistributionAmount = 500 * (10 ** uint(decimals));


  function LinkToken()
    public
  {
    balances[msg.sender] = creatorInitialBalance;
    uint _initPoolBalance = totalSupply - creatorInitialBalance;
    balances[this] = _initPoolBalance;
    poolBalance = _initPoolBalance;
  }

  function claimTokens(uint _amount)
    public
  {
    require(poolBalance >= _amount);
    poolBalance -= _amount;
    balances[this] -= _amount;
    balances[msg.sender] += _amount;
    transfer(msg.sender, _amount);
  }

  function () payable external {
      uint amount = tokenDistributionAmount; // Amount of LINK tokens to distribute        
      poolBalance -= amount;
      balances[this] -= amount;
      balances[msg.sender] += amount;
      transfer(msg.sender, amount);
  }

  /**
  * @dev transfer token to a specified address with additional data if the recipient is a contract.
  * @param _to The address to transfer to.
  * @param _value The amount to be transferred.
  * @param _data The extra data to be passed to the receiving contract.
  */
  function transferAndCall(address _to, uint _value, bytes _data)
    public
    validRecipient(_to)
    returns (bool success)
  {
    return super.transferAndCall(_to, _value, _data);
  }

  /**
  * @dev transfer token to a specified address.
  * @param _to The address to transfer to.
  * @param _value The amount to be transferred.
  */
  function transfer(address _to, uint _value)
    public
    validRecipient(_to)
    returns (bool success)
  {
    return super.transfer(_to, _value);
  }

  /**
   * @dev Approve the passed address to spend the specified amount of tokens on behalf of msg.sender.
   * @param _spender The address which will spend the funds.
   * @param _value The amount of tokens to be spent.
   */
  function approve(address _spender, uint256 _value)
    public
    validRecipient(_spender)
    returns (bool)
  {
    return super.approve(_spender,  _value);
  }

  /**
   * @dev Transfer tokens from one address to another
   * @param _from address The address which you want to send tokens from
   * @param _to address The address which you want to transfer to
   * @param _value uint256 the amount of tokens to be transferred
   */
  function transferFrom(address _from, address _to, uint256 _value)
    public
    validRecipient(_to)
    returns (bool)
  {
    return super.transferFrom(_from, _to, _value);
  }


  // MODIFIERS

  modifier validRecipient(address _recipient) {
    require(_recipient != address(0) && _recipient != address(this));
    _;
  }
}
