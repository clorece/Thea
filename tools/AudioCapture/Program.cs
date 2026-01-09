using NAudio.CoreAudioApi;
using NAudio.Wave;
using System.CommandLine;

/// <summary>
/// Audio capture tool for Rin - captures system audio via WASAPI loopback.
/// Uses Windows Audio Session API for reliable capture from the default speaker.
/// </summary>
class Program
{
    static async Task<int> Main(string[] args)
    {
        var durationOption = new Option<int>(
            name: "--duration",
            description: "Duration in seconds to capture",
            getDefaultValue: () => 5);

        var outputOption = new Option<string>(
            name: "--output",
            description: "Output file path (WAV format)",
            getDefaultValue: () => "capture.wav");

        var listOption = new Option<bool>(
            name: "--list",
            description: "List available audio devices",
            getDefaultValue: () => false);

        var streamOption = new Option<bool>(
            name: "--stream",
            description: "Stream mode - continuously capture and write to stdout",
            getDefaultValue: () => false);

        var rootCommand = new RootCommand("Rin Audio Capture - WASAPI Loopback");
        rootCommand.AddOption(durationOption);
        rootCommand.AddOption(outputOption);
        rootCommand.AddOption(listOption);
        rootCommand.AddOption(streamOption);

        rootCommand.SetHandler((duration, output, list, stream) =>
        {
            if (list)
            {
                ListDevices();
            }
            else if (stream)
            {
                StreamAudio();
            }
            else
            {
                CaptureToFile(duration, output);
            }
        }, durationOption, outputOption, listOption, streamOption);

        return await rootCommand.InvokeAsync(args);
    }

    static void ListDevices()
    {
        var enumerator = new MMDeviceEnumerator();
        
        Console.WriteLine("=== Audio Render Devices (Speakers) ===");
        foreach (var device in enumerator.EnumerateAudioEndPoints(DataFlow.Render, DeviceState.Active))
        {
            var isDefault = device.ID == enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia).ID;
            Console.WriteLine($"  {(isDefault ? "[DEFAULT] " : "")}{device.FriendlyName}");
        }
    }

    static void CaptureToFile(int durationSeconds, string outputPath)
    {
        try
        {
            var enumerator = new MMDeviceEnumerator();
            var device = enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
            
            Console.Error.WriteLine($"[AudioCapture] Using: {device.FriendlyName}");
            Console.Error.WriteLine($"[AudioCapture] Capturing {durationSeconds} seconds to: {outputPath}");

            using var capture = new WasapiLoopbackCapture(device);
            var writer = new WaveFileWriter(outputPath, capture.WaveFormat);
            
            capture.DataAvailable += (s, e) =>
            {
                writer.Write(e.Buffer, 0, e.BytesRecorded);
            };

            capture.RecordingStopped += (s, e) =>
            {
                writer.Dispose();
                if (e.Exception != null)
                {
                    Console.Error.WriteLine($"[AudioCapture] Error: {e.Exception.Message}");
                }
            };

            capture.StartRecording();
            Thread.Sleep(durationSeconds * 1000);
            capture.StopRecording();

            Console.Error.WriteLine($"[AudioCapture] Saved: {outputPath}");
            Console.Error.WriteLine($"[AudioCapture] Format: {capture.WaveFormat.SampleRate}Hz, {capture.WaveFormat.Channels}ch, {capture.WaveFormat.BitsPerSample}bit");
            
            // Output the file path to stdout for Python to read
            Console.WriteLine(outputPath);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[AudioCapture] Fatal: {ex.Message}");
            Environment.Exit(1);
        }
    }

    static void StreamAudio()
    {
        try
        {
            var enumerator = new MMDeviceEnumerator();
            var device = enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
            
            Console.Error.WriteLine($"[AudioCapture] Streaming from: {device.FriendlyName}");

            using var capture = new WasapiLoopbackCapture(device);
            
            // Write WAV header info to stderr so Python knows the format
            Console.Error.WriteLine($"[AudioCapture] Format: {capture.WaveFormat.SampleRate},{capture.WaveFormat.Channels},{capture.WaveFormat.BitsPerSample}");

            var stdout = Console.OpenStandardOutput();
            
            capture.DataAvailable += (s, e) =>
            {
                if (e.BytesRecorded > 0)
                {
                    stdout.Write(e.Buffer, 0, e.BytesRecorded);
                    stdout.Flush();
                }
            };

            capture.RecordingStopped += (s, e) =>
            {
                if (e.Exception != null)
                {
                    Console.Error.WriteLine($"[AudioCapture] Error: {e.Exception.Message}");
                }
            };

            capture.StartRecording();
            
            // Run until stdin is closed
            Console.Error.WriteLine("[AudioCapture] Streaming... (close stdin to stop)");
            while (Console.Read() != -1) { }
            
            capture.StopRecording();
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[AudioCapture] Fatal: {ex.Message}");
            Environment.Exit(1);
        }
    }
}
