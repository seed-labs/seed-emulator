import json

class ContractABIHelper:

    _abi: dict 

    def __init__(self, abi_file): 
        with open(abi_file, 'r') as f:
              self._abi = json.load(f)


    def is_local_call(self, func_name):
        """!
        @brief Check whether the call is a local call or a transaction call
        @return True of False
        """
        func = None
        for item in self._abi:
           if item['type'] == 'function' and item['name'] == func_name:
              func = item

        assert func != None, "Function does not exist"

        if func['stateMutability'] == 'view':
            return True
        else:
            return False

    
    def _convert_to_python_type(self, solidity_type):
        """!
        @brief Convert the solidity type to python type
        """
        if solidity_type == 'address':
            return 'str'
        elif solidity_type == 'string':
            return 'str'
        else:
            return 'int'
    

    def _get_constructor(self):
        """!
        @brief Retrieve the constructor function from the abi content
        """
        for item in self._abi:
            if item['type'] == 'constructor':
              return item

        assert False, "Constructor does not exist"


    def _get_function(self, func_name):
        """!
        @brief Retrieve the specified function from the abi content
        @param func_name The name of the function
        @param abi The abi content
        @return Return the dictionary of the function
        """
        for item in self._abi:
           if item['type'] == 'function' and item['name'] == func_name:
              return item
    
        assert False, "Function does not exist"
    
    
    def construct_arg_list(self, func_name, argv):
        """!
        @brief Construct the argument list based on the function signature
        @param func_name The function information from the abi content. If
               the value is None, it is the constructor
        @param argv The list of argument (in string format)
        @return Return the argument list
        """
    
        if func_name is None:
            func = self._get_constructor()
            print(func)
        else:
            func = self._get_function(func_name)

        assert len(func['inputs']) == len(argv), "Length of argument do not match"
    
        arg_list = []
        i = 0
        for input_ in func['inputs']:
            python_type = self._convert_to_python_type(input_['type'])
            if python_type == 'int':
                arg_list.append(int(argv[i]))
            elif python_type == 'str':
                arg_list.append(str(argv[i]))
            elif python_type == 'bool':
                arg_list.append(bool(argv[i]))
            i += 1
    
        return arg_list
    
    
