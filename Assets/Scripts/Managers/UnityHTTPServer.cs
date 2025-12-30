using UnityEngine;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.IO;

public class UnityHTTPServer : MonoBehaviour
{
    public VoiceActionReceiver receiver;

    private TcpListener server;
    private Thread serverThread;
    private bool running = false;

    void Start()
    {
        serverThread = new Thread(StartServer);
        serverThread.Start();
        Debug.Log("Unity TCP HTTP server started on port 5005");
    }

    void StartServer()
    {
        server = new TcpListener(System.Net.IPAddress.Any, 5005);
        server.Start();
        running = true;

        while (running)
        {
            try
            {
                TcpClient client = server.AcceptTcpClient();
                Thread clientThread = new Thread(() => HandleClient(client));
                clientThread.Start();
            }
            catch { }
        }
    }

    void HandleClient(TcpClient client)
    {
        using (NetworkStream stream = client.GetStream())
        {
            using (StreamReader reader = new StreamReader(stream))
            {
                string request = reader.ReadToEnd();

                // Extract JSON body from HTTP POST
                int jsonStart = request.IndexOf("{");
                int jsonEnd = request.LastIndexOf("}");

                if (jsonStart >= 0 && jsonEnd > jsonStart)
                {
                    string json = request.Substring(jsonStart, jsonEnd - jsonStart + 1);
                    Debug.Log("Received JSON: " + json);

                    // Pass to Unity main thread
                    UnityMainThreadDispatcher.Instance.Enqueue(() =>
                    {
                        receiver.OnReceive(json);
                    });
                }
            }

            // Send simple HTTP OK response
            string response =
                "HTTP/1.1 200 OK\r\n" +
                "Content-Type: text/plain\r\n" +
                "Content-Length: 2\r\n\r\nOK";

            byte[] buffer = Encoding.UTF8.GetBytes(response);
            stream.Write(buffer, 0, buffer.Length);
        }

        client.Close();
    }

    void OnApplicationQuit()
    {
        running = false;
        server.Stop();
    }
}
