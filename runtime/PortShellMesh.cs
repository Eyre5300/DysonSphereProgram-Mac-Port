using UnityEngine;
using UnityEngine.Rendering;

// Metal has no geometry stage. Reuse the original cell attributes at each of
// its twelve emitted vertices; the recovered shader computes each corner.
public static class PortShellMesh
{
    public static void Populate(Mesh mesh, Vector3[] positions, Vector2[] uv,
        Vector2[] uv2, Vector2[] uv3, int[] points)
    {
        int count = points.Length;
        var p = new Vector3[count * 12];
        var a = new Vector2[p.Length];
        var b = new Vector2[p.Length];
        var c = new Vector2[p.Length];
        var corner = new Vector2[p.Length];
        var triangles = new int[count * 18];
        for (int i = 0; i < count; i++)
        {
            int source = points[i];
            for (int j = 0; j < 12; j++)
            {
                int v = i * 12 + j;
                p[v] = positions[source]; a[v] = uv[source];
                b[v] = uv2[source]; c[v] = uv3[source];
                corner[v] = new Vector2(j, 0);
            }
            for (int strip = 0; strip < 3; strip++)
            {
                int v = i * 12 + strip * 4, t = i * 18 + strip * 6;
                triangles[t] = v; triangles[t + 1] = v + 1; triangles[t + 2] = v + 2;
                triangles[t + 3] = v + 2; triangles[t + 4] = v + 1; triangles[t + 5] = v + 3;
            }
        }
        mesh.indexFormat = IndexFormat.UInt32;
        mesh.vertices = p; mesh.uv = a; mesh.uv2 = b; mesh.uv3 = c; mesh.uv4 = corner;
        mesh.SetIndices(triangles, MeshTopology.Triangles, 0, false);
    }
}
