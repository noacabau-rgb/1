"""Real-ESRGAN (SRVGGNetCompact) on CPU without PyTorch.

The official .pth checkpoints are read with a minimal unpickler, rebuilt as an
ONNX graph (Conv + PReLU stack, DepthToSpace, nearest skip) and run with
onnxruntime.

    from sr import Upscaler
    up = Upscaler(denoise=0.5)
    big = up(bgr_uint8)          # x4
"""
import os
import pickle
import zipfile
import numpy as np
import onnx
from onnx import helper, TensorProto, numpy_helper
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))


def load_pth(path):
    zf = zipfile.ZipFile(path)
    prefix = zf.namelist()[0].split("/")[0]
    dtypes = {"FloatStorage": np.float32, "HalfStorage": np.float16, "LongStorage": np.int64}

    class Storage:
        def __init__(self, name):
            self.dtype = dtypes[name]

    def rebuild(storage, offset, size, stride, *args):
        dt, key = storage
        buf = np.frombuffer(zf.read(f"{prefix}/data/{key}"), dt)
        n = int(np.prod(size)) if size else 1
        arr = buf[offset:offset + n] if not stride or list(stride) == list(np.cumprod((list(size) + [1])[::-1])[::-1][1:]) \
            else np.lib.stride_tricks.as_strided(buf[offset:], size, [s * buf.itemsize for s in stride])
        return np.array(arr, np.float32).reshape(size)

    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if mod == "torch._utils" and name == "_rebuild_tensor_v2":
                return rebuild
            if mod == "torch" and name in dtypes:
                return name
            if mod == "collections" and name == "OrderedDict":
                import collections
                return collections.OrderedDict
            return super().find_class(mod, name)

        def persistent_load(self, pid):
            _, stype, key, _, _ = pid
            return (dtypes[stype if isinstance(stype, str) else stype], key)

    sd = U(zf.open(f"{prefix}/data.pkl")).load()
    return sd.get("params", sd.get("params_ema", sd))


def build_onnx(sd, scale=4):
    convs = sorted({int(k.split(".")[1]) for k in sd if k.endswith(".weight") and sd[k].ndim == 4})
    nodes, inits = [], []
    x = "input"
    for i, ci in enumerate(convs):
        w, b = sd[f"body.{ci}.weight"], sd[f"body.{ci}.bias"]
        inits += [numpy_helper.from_array(w, f"w{ci}"), numpy_helper.from_array(b, f"b{ci}")]
        nodes.append(helper.make_node("Conv", [x, f"w{ci}", f"b{ci}"], [f"c{ci}"], pads=[1, 1, 1, 1], kernel_shape=[3, 3]))
        x = f"c{ci}"
        pk = f"body.{ci + 1}.weight"
        if i < len(convs) - 1 and pk in sd:
            inits.append(numpy_helper.from_array(sd[pk].reshape(-1, 1, 1), f"p{ci}"))
            nodes.append(helper.make_node("PRelu", [x, f"p{ci}"], [f"a{ci}"]))
            x = f"a{ci}"
    nodes.append(helper.make_node("DepthToSpace", [x], ["ps"], blocksize=scale, mode="CRD"))
    inits.append(numpy_helper.from_array(np.array([1, 1, scale, scale], np.float32), "scales"))
    nodes.append(helper.make_node("Resize", ["input", "", "scales"], ["base"], mode="nearest"))
    nodes.append(helper.make_node("Add", ["ps", "base"], ["output"]))
    g = helper.make_graph(nodes, "srvgg",
                          [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, None, None])],
                          [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, None, None])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 8
    return m


class Upscaler:
    def __init__(self, denoise=0.5, threads=4):
        a = load_pth(os.path.join(HERE, "models/realesr-general-x4v3.pth"))
        if denoise < 1:  # deep network interpolation with the weak-denoise model, as in Real-ESRGAN
            b = load_pth(os.path.join(HERE, "models/realesr-general-wdn-x4v3.pth"))
            a = {k: denoise * a[k] + (1 - denoise) * b[k] for k in a}
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(build_onnx(a).SerializeToString(), opts, providers=["CPUExecutionProvider"])

    def __call__(self, bgr):
        x = bgr[..., ::-1].astype(np.float32).transpose(2, 0, 1)[None] / 255
        y = self.sess.run(None, {"input": x})[0][0]
        return (np.clip(y.transpose(1, 2, 0)[..., ::-1], 0, 1) * 255 + 0.5).astype(np.uint8)
