from typing import List


def extend_and_unique(origin: List, elements: List):
    """Extend the list and make it no duplicate elements

    Args:
        origin: The array wants to be extend
        elements: The array waiting to be added into other arrays
    """
    for element in elements:
        if element not in origin:
            origin.append(element)



