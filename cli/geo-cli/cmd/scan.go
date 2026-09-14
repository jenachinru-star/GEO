package cmd

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/spf13/cobra"
)

var scanCmd = &cobra.Command{
	Use:   "scan",
	Short: "触发全量采集或单个问题采集",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("开始采集...")

		payload := map[string]interface{}{
			"detect_round": 1,
		}
		if len(args) > 0 {
			// 如果传入了问题ID，只采集单个问题
			var qid int
			fmt.Sscanf(args[0], "%d", &qid)
			payload["question_id"] = qid
			fmt.Printf("采集问题ID: %d\n", qid)
		} else {
			fmt.Println("执行全量采集...")
		}

		jsonData, _ := json.Marshal(payload)
		resp, err := http.Post(apiBaseURL+"/monitor/collect", "application/json", bytes.NewBuffer(jsonData))
		checkError(err)
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		var result map[string]interface{}
		json.Unmarshal(body, &result)

		if data, ok := result["data"].(map[string]interface{}); ok {
			fmt.Println("\n========== 采集结果 ==========")
			fmt.Printf("问题总数: %v\n", data["total"])
			fmt.Printf("成功: %v\n", data["success"])
			fmt.Printf("记录数: %v\n", data["records_count"])
			if platforms, ok := data["platforms"].([]interface{}); ok {
				fmt.Print("平台: ")
				for i, p := range platforms {
					if i > 0 {
						fmt.Print(", ")
					}
					fmt.Print(p)
				}
				fmt.Println()
			}
			fmt.Println("============================")
		}
	},
}
