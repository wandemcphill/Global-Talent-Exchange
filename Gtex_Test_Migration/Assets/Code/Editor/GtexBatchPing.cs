using System;
using System.IO;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexBatchPing
    {
        public static void Run()
        {
            Debug.Log("[GTEX Ping] ENTER");

            var markerPath = Path.GetFullPath(
                Path.Combine(
                    Directory.GetCurrentDirectory(),
                    "tmp",
                    "unity_batch_ping.txt"));

            var markerDirectory = Path.GetDirectoryName(markerPath);
            if (!string.IsNullOrWhiteSpace(markerDirectory))
            {
                Directory.CreateDirectory(markerDirectory);
            }

            File.WriteAllText(
                markerPath,
                DateTime.Now.ToString("O") + " GtexBatchPing.Run" + Environment.NewLine);

            Debug.Log("[GTEX Ping] Marker=" + markerPath);
        }
    }
}
