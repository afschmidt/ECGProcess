==============
Raising issues
==============

If you find a possible bug or improvement (in code and/or documentation) please
feel free to either fix this yourself following the *Contributing to the 
project* guidance, or by raising an issue on GitLab. 

When raising an issue please make sure to include a **minimal reproducible 
example** (MRE).
An MRE is a small, self-contained snippet of code that demonstrates the 
problem.
It includes only what's essential to reproduce the issue and nothing more. 

Including an MRE increases the chance that we are addressing the actual bug 
you have encountered. 
Furthermore, by spending to time to create an MRE, you may find a way to fix
it yourself - or, if not, meaningfully decrease the time we have to spend 
creating an MRE ourselves. 
This ensures that time can be spent on fixing the actual bug. 

**Steps for a Good MRE**

#. *Include Minimal Input Data*: Simplify your data to the smallest size and 
   complexity needed. Please have a look at the examples module for relevant
   example data. 
#. *Use Only Relevant Code*: Remove unrelated code or logic.
#. *Import Necessary Modules*: Include all imports and dependencies.
#. *State Expected vs. Actual Behavior*: Clearly describe what you expect and 
   what’s happening instead.

An example MRE
--------------

**Problem**: A function to calculate the mean throws an error with certain 
input.

**The MRE**

.. code-block:: python
   
    # Required imports
    import numpy as np
    
    # Minimal data causing the issue
    data = [1, 2, None, 4] 
    
    # Problematic code: Numpy does not handle None values
    mean_value = np.mean(data)  
    
    print(mean_value)
    
    # Expected behavior: Compute the mean and return a number.
    # Actual problem: TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'

**Key Tips for an MRE**

#. *Use Built-in Modules and Data*: If possible, use common libraries or 
   default data types (e.g. lists, dictionaries) to simplify sharing.
#. *Make It Copy-Paste Friendly*: Ensure someone can run your code without
   needing additional setup.
#. *Simplify the Problem*: If the issue is with a large function, isolate the 
   problematic part into a smaller example.

You could additionally consider including the original error message.
This might not be relevant if you have ensured the MRE faitfully replicates 
the same message. 

.. code-block:: python

    # Example error message
    mean_value = np.mean(data)  
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "<REDACTED>/python3.12/site-packages/numpy/core/fromnumeric.py",
      line 3504, in mean
        return _methods._mean(a, axis=axis, dtype=dtype,
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      File "<REDACTED>/python3.12/site-packages/numpy/core/_methods.py",
      line 118, in _mean
        ret = umr_sum(arr, axis, dtype, out, keepdims, where=where)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'

**Things that are less helpful**

- Sharing truncated error messages.
- Screenshots of your code or output. 

Many thanks in advance!


