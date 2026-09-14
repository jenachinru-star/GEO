package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/spf13/cobra"
)

var competitorCmd = &cobra.Command{
	Use:   "comp",
	Short: "竞品分析",
}

var compListCmd = &cobra.Command{
	Use:   "list",
	Short: "列出所有竞品",
	Run: func(cmd *cobra.Command, args []string) {
		resp, err := http.Get(apiBaseURL + "/competitor")
		checkError(err)
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		var result map[string]interface{}
		json.Unmarshal(body, &result)

		if items, ok := result["data"].([]interface{}); ok {
			fmt.Printf("共 %d 个竞品:\n\n", len(items))
			for _, item := range items {
				c := item.(map[string]interface{})
				fmt.Printf("- %s", c["name"])
				if c["industry"] != "" {
					fmt.Printf(" (%s)", c["industry"])
				}
				fmt.Println()
			}
		}
	},
}

var compRecordsCmd = &cobra.Command{
	Use:   "records",
	Short: "查看竞品监测记录",
	Run: func(cmd *cobra.Command, args []string) {
		resp, err := http.Get(apiBaseURL + "/competitor/records")
		checkError(err)
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		var result map[string]interface{}
		json.Unmarshal(body, &result)

		if items, ok := result["data"].([]interface{}); ok {
			fmt.Printf("共 %d 条监测记录:\n\n", len(items))
			for _, item := range items {
				r := item.(map[string]interface{})
				rank := "未提及"
				if r["mentioned"].(bool) {
					rank = fmt.Sprintf("第%.0f名", r["rank"])
				}
				fmt.Printf("[%s] %s - %s\n", r["detect_date"], r["platform_code"], rank)
			}
		}
	},
}

func init() {
	competitorCmd.AddCommand(compListCmd)
	competitorCmd.AddCommand(compRecordsCmd)
}
