==============
Raising issues
==============

If you find a possible bug or improvement (in code and/or documentation) please feel free to either fix this yourself following the *Contributing to the project* guidance, 
or by raising an issue on GitLab. 

When raising an issue please make sure to include a **minimal reproducible example** (MRE).  An MRE is a small, self-contained snippet of code that demonstrates the problem.
It includes only what's essential to reproduce the issue and nothing more.

Including an MRE increases the change that we are addressing the actual bug you have encountered. 
Furthermore, by spending to time to create an MRE you may find a way to fix it yourself, or if not, meaningfully decrease the time we have to spend creating 
an MRE ourselves and therefore ensures the time can be spent on fixing the actual bug. 

**Steps for a Good MRE**
#. Include Minimal Input Data: Simplify your data to the smallest size and complexity needed.
#. Use Only Relevant Code: Remove unrelated code or logic.
#. Import Necessary Modules: Include all imports and dependencies.
#. State Expected vs. Actual Behavior: Clearly describe what you expect and what’s happening instead.

An example MRE
--------------

*Problem*: A function to calculate the mean throws an error with certain input.

*The MRE*

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

*Key Tips for a MRE*
#. **Use Built-in Modules and Data**: If possible, use common libraries or Python data types (e.g., lists, dictionaries) to simplify sharing.
#. **Make It Copy-Paste Friendly**: Ensure someone can run your code without needing additional setup.
#. **Simplify the Problem**: If the issue is with a large function, isolate the problematic part into a smaller example.

Many thanks in advance!


