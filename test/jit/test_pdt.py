import os
import sys
import torch
from torch.testing._internal.jit_utils import JitTestCase, make_global
from torch.jit._monkeytype_config import _IS_MONKEYTYPE_INSTALLED
from typing import List, Dict, Tuple, Any  # noqa: F401

# Make the helper files in test/ importable
pytorch_test_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(pytorch_test_dir)

if not _IS_MONKEYTYPE_INSTALLED:
    print("monkeytype is not installed. Skipping tests for Profile-Directed Typing", file=sys.stderr)
    JitTestCase = object  # type: ignore[misc, assignment] # noqa: F811

if __name__ == "__main__":
    raise RuntimeError(
        "This test file is not meant to be run directly, use:\n\n"
        "\tpython test/test_jit.py TESTNAME\n\n"
        "instead."
    )

class TestPDT(JitTestCase):
    """
    A suite of tests for profile directed typing in TorchScript.
    """
    def test_pdt(self):
        def test_sum(a, b):
            return a + b

        make_global(test_sum)
        scripted_fn_add = torch.jit._script_pdt(test_sum, example_inputs=[(3, 4)])
        self.assertEqual(scripted_fn_add(10, 2), test_sum(10, 2))

        def test_sub(a, b):
            return a - b

        make_global(test_sub)
        scripted_fn_sub = torch.jit._script_pdt(test_sub, example_inputs=[(3.9, 4.10)])
        self.assertEqual(scripted_fn_sub(6.5, 2.9), test_sub(6.5, 2.9))

        def test_mul(a, b):
            return a * b

        make_global(test_mul)
        scripted_fn_mul = torch.jit._script_pdt(test_mul, example_inputs=[(-10, 9)])
        self.assertEqual(scripted_fn_mul(-1, 3), test_mul(-1, 3))

        def test_args_complex(real, img):
            return torch.complex(real, img)

        make_global(test_args_complex)
        scripted_fn_complex = torch.jit._script_pdt(test_args_complex, example_inputs=[(torch.rand(3, 4), torch.rand(3, 4))])
        arg1, arg2 = torch.rand(3, 4), torch.rand(3, 4)
        self.assertEqual(scripted_fn_complex(arg1, arg2), test_args_complex(arg1, arg2))

        def test_bool(a):
            if a:
                return -1
            else:
                return 0

        make_global(test_bool)
        scripted_fn_bool = torch.jit._script_pdt(test_bool, example_inputs=[(True,)])
        self.assertEqual(scripted_fn_bool(True), test_bool(True))

        def test_str(a):
            if a == "":
                return False
            else:
                return True

        make_global(test_str)
        scripted_fn_str = torch.jit._script_pdt(test_str, example_inputs=[("",)])
        self.assertEqual(scripted_fn_str("abc"), test_str("abc"))

    def test_pdt_list_and_tuple(self):
        def test_list_and_tuple(a):
            return sum(a)

        make_global(test_list_and_tuple)

        scripted_fn_float = torch.jit._script_pdt(test_list_and_tuple, example_inputs=[([4.9, 8.9],)])
        self.assertEqual(scripted_fn_float([11.9, 7.6]), test_list_and_tuple([11.9, 7.6]))

        scripted_fn_bool = torch.jit._script_pdt(test_list_and_tuple, example_inputs=[([True, False, True],)])
        self.assertEqual(scripted_fn_bool([True, True, True]), test_list_and_tuple([True, True, True]))

        scripted_fn_int = torch.jit._script_pdt(test_list_and_tuple, example_inputs=[([3, 4, 5], )])
        self.assertEqual(scripted_fn_int([1, 2, 3]), test_list_and_tuple([1, 2, 3]))

        scripted_fn_float = torch.jit._script_pdt(test_list_and_tuple, example_inputs=[((4.9, 8.9),)])
        self.assertEqual(scripted_fn_float((11.9, 7.6)), test_list_and_tuple((11.9, 7.6)))

        scripted_fn_bool = torch.jit._script_pdt(test_list_and_tuple,
                                                 example_inputs=[((True, False, True),)])
        self.assertEqual(scripted_fn_bool((True, True, True)),
                         test_list_and_tuple((True, True, True)))

        scripted_fn_int = torch.jit._script_pdt(test_list_and_tuple, example_inputs=[((3, 4, 5), )])
        self.assertEqual(scripted_fn_int((1, 2, 3)), test_list_and_tuple((1, 2, 3)))

    def test_pdt_dict(self):
        def test_dict(a):
            return a['foo']

        def test_dict_int_list(a):
            return a[1]

        make_global(test_dict, test_dict_int_list)

        str_bool_inp = {'foo' : True, 'bar': False}
        scripted_fn = torch.jit._script_pdt(test_dict, example_inputs=[(str_bool_inp,)])
        self.assertEqual(scripted_fn({'foo' : False, 'bar': True}, ), test_dict({'foo' : False, 'bar': True}, ))

        str_list_inp = {0 : [True, False], 1: [False, True]}
        scripted_fn = torch.jit._script_pdt(test_dict_int_list, example_inputs=[(str_list_inp,)])
        self.assertEqual(scripted_fn({0 : [False, False], 1: [True, True]}, ),
                         test_dict_int_list({0 : [False, False], 1: [True, True]}, ))

    def test_any(self):
        def test_multiple_types(a):
            assert not isinstance(a, bool)
            return a

        def test_multiple_type_refinement(a):
            if isinstance(a, bool):
                return 1
            elif isinstance(a, int):
                return 1 + a
            elif isinstance(a, float):
                return 1 + int(a)
            else:
                return -1

        make_global(test_multiple_types, test_multiple_type_refinement)

        scripted_fn = torch.jit._script_pdt(test_multiple_types, example_inputs=[(1,), ("abc", ), (8.9,), ([3, 4, 5], )])
        self.assertEqual(scripted_fn(10), test_multiple_types(10))
        self.assertEqual(scripted_fn("def"), test_multiple_types("def"))
        self.assertEqual(scripted_fn(7.89999), test_multiple_types(7.89999))
        self.assertEqual(scripted_fn([10, 11, 14]), test_multiple_types([10, 11, 14]))

        scripted_fn = torch.jit._script_pdt(test_multiple_type_refinement, example_inputs=[(1,), ("abc", ), (8.9,),
                                              ([3, 4, 5],), (True, ), ({"a": True}, ), ])
        self.assertEqual(scripted_fn(10), test_multiple_type_refinement(10))
        self.assertEqual(scripted_fn("def"), test_multiple_type_refinement("def"))
        self.assertEqual(scripted_fn(7.89999), test_multiple_type_refinement(7.89999))
        self.assertEqual(scripted_fn([10, 11, 14]), test_multiple_type_refinement([10, 11, 14]))
        self.assertEqual(scripted_fn(False), test_multiple_type_refinement(False))
        self.assertEqual(scripted_fn({"abc" : True, "def": False}), test_multiple_type_refinement({"abc" : True, "def": False}))

    def test_class_as_profiled_types(self):
        class UserDefinedClass:
            def fn(self, b):
                assert b is not None
                return b

        def test_model(a, m):
            assert not isinstance(a, bool)
            return m.fn(a)

        make_global(UserDefinedClass, test_model)

        user_class = UserDefinedClass()
        scripted_fn = torch.jit._script_pdt(test_model, example_inputs=[(10, user_class, ), (10.9, user_class, ), ])
        self.assertEqual(scripted_fn(100, user_class, ), test_model(100, user_class))
        self.assertEqual(scripted_fn(1.9, user_class, ), test_model(1.9, user_class))

    def test_class_with_args_as_profiled_types(self):
        class ClassWithArgs:
            def __init__(self, a: bool):
                self.a = a

            def fn(self, b):
                if self.a:
                    return b
                else:
                    return -1

        def test_model_with_args(a, m):
            assert not isinstance(a, bool)
            return m.fn(a)

        make_global(ClassWithArgs, test_model_with_args)

        user_class = ClassWithArgs(False)
        scripted_fn = torch.jit._script_pdt(test_model_with_args, example_inputs=[(10, user_class, ), (10.9, user_class, ), ])
        self.assertEqual(scripted_fn(100, ClassWithArgs(True), ), test_model_with_args(100, ClassWithArgs(True)))

    def test_nn_module(self):
        class TestPDTModel(torch.nn.Module):
            def __init__(self):
                super().__init__()

            def forward(self, x) -> Any:
                if isinstance(x, int):
                    return x + 1
                elif isinstance(x, float):
                    return x - 1
                else:
                    return x

        make_global(TestPDTModel)
        pdt_model = TestPDTModel()
        scripted_pdt_model = torch.jit._script_pdt(pdt_model, example_inputs=[(10, ), (10.80, ), (False, )])
        self.assertEqual(scripted_pdt_model(50), pdt_model(50))
        self.assertEqual(scripted_pdt_model(1.8), pdt_model(1.8))
        self.assertTrue(scripted_pdt_model(True), pdt_model(True))

    def test_nested_nn_module_class(self):
        class NestedPDTInner(torch.nn.Module):
            def __init__(self):
                super().__init__()

            def forward(self, x):
                if isinstance(x, int):
                    return x * 10
                return x

        class NestedModulePDTWrapper(torch.nn.Module):
            def __init__(self, inner):
                super().__init__()
                self.inner = inner

            def forward(self, x):
                return self.inner(x)

        make_global(NestedPDTInner, NestedModulePDTWrapper)
        inner_pdt_model = NestedPDTInner()
        wrapped_pdt_model = NestedModulePDTWrapper(inner_pdt_model)
        scripted_pdt_model = torch.jit._script_pdt(wrapped_pdt_model, example_inputs=[(20, ), (2.7, ), (False, )])
        self.assertEqual(scripted_pdt_model(30), wrapped_pdt_model(30))
        self.assertEqual(scripted_pdt_model(1.9), wrapped_pdt_model(1.9))
        self.assertTrue(scripted_pdt_model(True), wrapped_pdt_model(True))

    def test_nested_function_in_forward(self):
        class NestedFunctionInForward(torch.nn.Module):
            def __init__(self):
                super().__init__()

            def forward(self, x):
                return self.fun(x) + 10

            def fun(self, x):
                if isinstance(x, bool):
                    return 0
                elif isinstance(x, int):
                    return x + 1
                return 0

        make_global(NestedFunctionInForward)
        pdt_model = NestedFunctionInForward()
        scripted_pdt_model = torch.jit._script_pdt(pdt_model, example_inputs=[(20, ), (False, )])
        self.assertEqual(scripted_pdt_model(30), pdt_model(30))
        self.assertEqual(scripted_pdt_model(True), pdt_model(True))
