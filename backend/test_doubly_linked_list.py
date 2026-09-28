"""Smoke tests for the AquaRuta doubly linked list.

Run with: python test_doubly_linked_list.py
"""

from app import CLOSED, OPEN, DoublyLinkedList, TrunkMain


def check(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)
    print(f"OK - {message}")


def main():
    dll = DoublyLinkedList()
    check(dll.is_empty(), "a new list is empty")

    dll.add_last("Compuerta de Admision", 3240, OPEN)
    dll.add_last("Camara Central", 3130, OPEN)
    dll.add_first("Ducto de Derivacion", 3260, CLOSED)
    check(len(dll) == 3, "size is 3 after 3 insertions")
    check([v["name"] for v in dll.to_list_forward()][0] == "Ducto de Derivacion",
          "add_first places the chamber at the head")
    check([v["name"] for v in dll.to_list_backward()][0] == "Camara Central",
          "backward traversal uses prev pointers correctly")

    dll.insert_at(1, "Cruce Calle 45", 3160, CLOSED)
    check(dll.to_list_forward()[1]["name"] == "Cruce Calle 45", "insert_at works")
    check(dll.to_list_forward()[1]["status"] == CLOSED, "insert_at keeps the status")

    head_id = dll.head.valve_id
    dll.insert_after(head_id, "Purga", 3220, CLOSED)
    check(len(dll) == 5, "insert_after increases the size")

    found = dll.find_by_name("camara")
    check(len(found) == 1 and found[0]["name"] == "Camara Central",
          "search by name works without accents")
    check(dll.count_by_status(CLOSED) == 3, "count_by_status counts closed chambers")
    check(dll.count_by_status(OPEN) == 2, "count_by_status counts open chambers")

    dll.remove_first()
    dll.remove_last()
    check(len(dll) == 3, "remove_first and remove_last work")

    check([v["name"] for v in dll.to_list_forward()] == ["Purga", "Cruce Calle 45", "Compuerta de Admision"],
          "list order after removing both ends")
    dll.remove_at(1)
    check([v["name"] for v in dll.to_list_forward()] == ["Purga", "Compuerta de Admision"],
          "remove_at removes the right chamber")

    trunk = TrunkMain()
    check(len(trunk.valves) == 8, "the demo trunk main has 8 chambers")
    first_id = trunk.current().valve_id
    trunk.move("downstream")
    check(trunk.current().valve_id != first_id, "the operator moves downstream (next)")
    trunk.move("upstream")
    check(trunk.current().valve_id == first_id, "the operator moves upstream (prev)")

    downstream_id = trunk.current().valve_id
    trunk.current_id = trunk.valves.tail.valve_id
    outcome = trunk.move("downstream")[1]
    check(outcome == "end_of_line", "the operator cannot pass the reservoir end")
    trunk.remove(downstream_id)
    check(trunk.current().valve_id == trunk.valves.tail.valve_id,
          "removing the operator chamber keeps the cursor on a valid node")

    trunk.seed_demo()
    trunk.current_id = trunk.valves.tail.valve_id
    trunk.remove_last()
    check(trunk.current().valve_id == trunk.valves.tail.valve_id,
          "removing the tail keeps the operator on the new tail")

    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
