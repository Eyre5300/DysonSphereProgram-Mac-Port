using System;
using System.IO;
using Unity.Collections.LowLevel.Unsafe;
using UnityEngine;

// Read the existing native asset storage without TextAsset.bytes' full managed copy.
// The caller must not destroy/unload the asset while reading. This private adapter is
// used synchronously by HashSystem.LoadBucketMap, with Configs also owning the asset.
public static class DSPPadTextAssetStream
{
    public static unsafe Stream OpenRead(TextAsset asset)
    {
        if (asset == null) throw new ArgumentNullException(nameof(asset));
        var data = asset.GetData<byte>(); // borrowed; never Dispose this NativeArray
        if (data.Length == 0) return new MemoryStream(Array.Empty<byte>(), false);
        var stream = new BorrowedStream(asset,
            (byte*)NativeArrayUnsafeUtility.GetUnsafeReadOnlyPtr(data), data.Length);
        GC.KeepAlive(asset);
        return stream;
    }

    sealed unsafe class BorrowedStream : UnmanagedMemoryStream
    {
        TextAsset owner;
        internal BorrowedStream(TextAsset asset, byte* data, long length)
            : base(data, length, length, FileAccess.Read) { owner = asset; }
        protected override void Dispose(bool disposing)
        {
            var retainedOwner = owner;
            try { base.Dispose(disposing); }
            finally { GC.KeepAlive(retainedOwner); owner = null; }
        }
    }
}
