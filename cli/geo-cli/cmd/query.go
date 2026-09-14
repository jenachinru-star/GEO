package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"

	"github.com/spf13/cobra"
)

var (
	queryPlatform string
)

var queryCmd = &cobra.Command{
	Use:   "query [问题内容]",
	Short: "查询单个问题在各平台的排名情况",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		question := args[0]
		fmt.Printf("查询问题: %s\n", question)
		if queryPlatform != "" {
			fmt.Printf("指定平台: %s\n", queryPlatform)
		}
		fmt.Println("正在查询...")

		// 先获取问题列表找到匹配的问题
		resp, err := http.Get(apiBaseURL + "/monitor/questions?keyword=" + url.QueryEscape(question) + "&page_size=5")
		checkError(err)
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		var result map[string]interface{}
		json.Unmarshal(body, &result)

		if data, ok := result["data"].(map[string]interface{}); ok {
			if items, ok := data["items"].([]interface{}); ok && len(items) > 0 {
				q := items[0].(map[string]interface{})
				qid := int(q["id"].(float64))
				fmt.Printf("\n找到监测问题 (ID: %d): %s\n", qid, q["question"])

				// 获取趋势
				trendURL := fmt.Sprintf("%s/monitor/trend/%d?days=7", apiBaseURL, qid)
				if queryPlatform != "" {
					trendURL += "&platform_code=" + queryPlatform
				}
				resp2, err := http.Get(trendURL)
				checkError(err)
				defer resp2.Body.Close()

				body2, _ := io.ReadAll(resp2.Body)
				var result2 map[string]interface{}
				json.Unmarshal(body2, &result2)

				if trends, ok := result2["data"].([]interface{}); ok && len(trends) > 0 {
					fmt.Println("\n近7天排名趋势:")
					fmt.Println("日期        平台      排名  提及")
					fmt.Println("--------------------------------")
					for _, t := range trends {
						trend := t.(map[string]interface{})
						rank := "未提及"
						if trend["rank"].(float64) > 0 {
							rank = fmt.Sprintf("第%.0f名", trend["rank"])
						}
						mentioned := "否"
						if trend["mentioned"].(bool) {
							mentioned = "是"
						}
						fmt.Printf("%s  %-8s  %-6s %s\n",
							trend["date"], trend["platform"], rank, mentioned)
					}
				} else {
					fmt.Println("\n暂无历史监测数据，请先执行采集")
				}
			} else {
				fmt.Println("\n未找到匹配的监测问题，可使用 'geo scan' 触发采集")
			}
		}
	},
}

func init() {
	queryCmd.Flags().StringVarP(&queryPlatform, "platform", "p", "", "指定平台 (deepseek/glm/doubao/qwen)")
}
