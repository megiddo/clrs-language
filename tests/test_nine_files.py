"""The checklist's nine-file table, run through the Engine facade on the real example files."""

import unittest
from pathlib import Path

from clrs import CompileError
from clrs import Engine
from clrs import RuntimeFault
from clrs.bytecode import IntegerConstant
from clrs.values import ClrsArray

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
UNSORTED = "[5, 2, 4, 6, 1, 3]"
HEAP_INPUT = "[4, 1, 3, 2, 16, 9, 10, 14, 8, 7]"
HEAP_FAMILY = ("heap.clrs", "max-heapify.clrs", "build-max-heap.clrs", "heapsort.clrs")


def engine(*names: str) -> Engine:
    return Engine.of(*[EXAMPLES / name for name in names])


def items(value: object) -> tuple[object, ...]:
    assert isinstance(value, ClrsArray)
    return value.items()


class SortTest(unittest.TestCase):
    def test_insertion_sort(self) -> None:
        result = engine("insertion-sort.clrs").run(f"A ← {UNSORTED}; InsertionSort(A); A")
        self.assertEqual(items(result), (1, 2, 3, 4, 5, 6))

    def test_bubblesort(self) -> None:
        result = engine("bubblesort.clrs").run(f"A ← {UNSORTED}; BubbleSort(A); A")
        self.assertEqual(items(result), (1, 2, 3, 4, 5, 6))

    def test_sorts_share_one_module_and_sort_in_place(self) -> None:
        both = engine("insertion-sort.clrs", "bubblesort.clrs")
        self.assertEqual(both.modules(), ("Clrs.Sorting",))
        for name in ("InsertionSort", "BubbleSort"):
            result = both.run(f"A ← [3, 1, 2]; B ← A; {name}(A); B")
            self.assertEqual(items(result), (1, 2, 3))


class MergeTest(unittest.TestCase):
    def test_merge_compiles(self) -> None:
        listing = engine("merge.clrs").listing("Clrs.Sorting")
        self.assertIn(".proc Merge\n", listing)
        self.assertIn("▷ R[i] ← A[q + j]\n", listing)

    def test_merge_real_range_faults_on_nil(self) -> None:
        with self.assertRaises(RuntimeFault) as caught:
            engine("merge.clrs").run("A ← [2, 1]; Merge(A, 1, 1, 2); A")
        self.assertEqual(caught.exception.message, "NIL cannot be compared.")

    def test_mergesort_one_element_is_unchanged(self) -> None:
        result = engine("mergesort.clrs").run("A ← [5,]; MergeSort(A, 1, 1); A")
        self.assertEqual(items(result), (5,))

    def test_mergesort_wider_range_with_merge_faults_on_nil(self) -> None:
        with self.assertRaises(RuntimeFault) as caught:
            engine("merge.clrs", "mergesort.clrs").run("A ← [2, 1]; MergeSort(A, 1, 2); A")
        self.assertEqual(caught.exception.message, "NIL cannot be compared.")

    def test_mergesort_wider_range_without_merge_has_no_procedure(self) -> None:
        with self.assertRaises(RuntimeFault) as caught:
            engine("mergesort.clrs").run("A ← [2, 1]; MergeSort(A, 1, 2); A")
        self.assertEqual(caught.exception.message, "Merge is not a loaded procedure.")


class LinearSearchTest(unittest.TestCase):
    def test_compile_error_on_line_5(self) -> None:
        with self.assertRaises(CompileError) as caught:
            engine("linear-search.clrs")
        self.assertEqual(caught.exception.line, 5)


class HeapTest(unittest.TestCase):
    def test_left_and_right(self) -> None:
        heap = engine("heap.clrs")
        self.assertEqual(heap.run("A ← [1, 2]; left[A, 1]"), 3)
        self.assertEqual(heap.run("A ← [1, 2]; right[A, 1]"), 4)

    def test_heap_family_permutation(self) -> None:
        result = engine(*HEAP_FAMILY).run(f"A ← {HEAP_INPUT}; HeapSort(A); A")
        self.assertEqual(items(result), (16, 1, 2, 3, 9, 4, 7, 8, 10, 14))

    def test_heap_family_contains(self) -> None:
        result = engine(*HEAP_FAMILY).run(f"A ← {HEAP_INPUT}; HeapSort(A); contains[A]")
        self.assertEqual(result, 1)

    def test_heap_records_default_and_does_not_apply_it(self) -> None:
        heap = engine("heap.clrs")
        record = heap.datatype("Heap")
        self.assertEqual((record.base, record.defaults), ("Array", (("contains", IntegerConstant(0)),)))
        with self.assertRaises(RuntimeFault) as caught:
            heap.run("A ← [1, 2]; contains[A]")
        self.assertEqual(caught.exception.message, "contains has not been set on this array.")


if __name__ == "__main__":
    unittest.main()
