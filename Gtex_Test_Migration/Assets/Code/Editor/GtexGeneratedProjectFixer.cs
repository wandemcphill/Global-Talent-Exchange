#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public sealed class GtexGeneratedProjectFixer : AssetPostprocessor
    {
        private static readonly string[] ExplicitPatterns =
        {
            @"Assets\Code\GTEX\**\*.cs",
            @"Assets\Code\MatchEngine\Players\Behaviours\OriginalRuntime*.cs"
        };

        public static string OnGeneratedCSProject(string path, string content)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(path) ||
                    string.IsNullOrWhiteSpace(content) ||
                    !path.EndsWith("Assembly-CSharp.csproj", StringComparison.OrdinalIgnoreCase))
                {
                    return content;
                }

                var requiredFiles = ResolveRequiredCompileIncludes();
                if (requiredFiles.Count == 0)
                {
                    return content;
                }

                var document = XDocument.Parse(content);
                XNamespace ns = document.Root != null ? document.Root.Name.Namespace : XNamespace.None;
                var existing = new HashSet<string>(
                    document.Descendants(ns + "Compile")
                        .Select(node => (string)node.Attribute("Include"))
                        .Where(value => !string.IsNullOrWhiteSpace(value)),
                    StringComparer.OrdinalIgnoreCase);

                var compileGroup = document.Descendants(ns + "ItemGroup")
                    .FirstOrDefault(group => group.Elements(ns + "Compile").Any());
                if (compileGroup == null)
                {
                    return content;
                }

                var added = 0;
                for (var index = 0; index < requiredFiles.Count; index += 1)
                {
                    var include = requiredFiles[index];
                    if (existing.Contains(include))
                    {
                        continue;
                    }

                    compileGroup.Add(new XElement(ns + "Compile", new XAttribute("Include", include)));
                    existing.Add(include);
                    added += 1;
                }

                if (added > 0)
                {
                    Debug.Log("[GTEX ProjectFix] Injected " + added + " compile include(s) into " + Path.GetFileName(path) + ".");
                    return document.Declaration != null
                        ? document.Declaration + Environment.NewLine + document
                        : document.ToString();
                }
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX ProjectFix] Failed to patch generated csproj.\n" + exception);
            }

            return content;
        }

        private static List<string> ResolveRequiredCompileIncludes()
        {
            var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var includes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            for (var patternIndex = 0; patternIndex < ExplicitPatterns.Length; patternIndex += 1)
            {
                var pattern = ExplicitPatterns[patternIndex];
                foreach (var relativePath in ExpandPattern(projectRoot, pattern))
                {
                    includes.Add(relativePath);
                }
            }

            return includes.OrderBy(value => value, StringComparer.OrdinalIgnoreCase).ToList();
        }

        private static IEnumerable<string> ExpandPattern(string projectRoot, string pattern)
        {
            if (string.IsNullOrWhiteSpace(projectRoot) || string.IsNullOrWhiteSpace(pattern))
            {
                yield break;
            }

            var normalizedPattern = pattern.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar);
            var recursiveToken = string.Concat(Path.DirectorySeparatorChar, "**", Path.DirectorySeparatorChar);
            var recursiveIndex = normalizedPattern.IndexOf(recursiveToken, StringComparison.Ordinal);
            string searchRoot;
            string filePattern;
            SearchOption searchOption;

            if (recursiveIndex >= 0)
            {
                searchRoot = normalizedPattern.Substring(0, recursiveIndex);
                filePattern = normalizedPattern.Substring(recursiveIndex + recursiveToken.Length);
                searchOption = SearchOption.AllDirectories;
            }
            else
            {
                searchRoot = Path.GetDirectoryName(normalizedPattern) ?? string.Empty;
                filePattern = Path.GetFileName(normalizedPattern);
                searchOption = SearchOption.TopDirectoryOnly;
            }

            var absoluteSearchRoot = Path.Combine(projectRoot, searchRoot);
            if (!Directory.Exists(absoluteSearchRoot))
            {
                yield break;
            }

            var files = Directory.GetFiles(absoluteSearchRoot, filePattern, searchOption);
            for (var index = 0; index < files.Length; index += 1)
            {
                var relativePath = Path.GetRelativePath(projectRoot, files[index]).Replace(Path.DirectorySeparatorChar, '\\');
                yield return relativePath;
            }
        }
    }
}
#endif
