package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/spf13/cobra"
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "查看系统状态和监测概览",
	Run: func(cmd *cobra.Command, args []string) {
		// 获取系统信息
		resp, err := http.Get(apiBaseURL + "/system/info")
		checkError(err)
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		var result map[string]interface{}
		json.Unmarshal(body, &result)

		if data, ok := result["data"].(map[string]interface{}); ok {
			fmt.Println("========== GEO 系统状态 ==========")
			fmt.Printf("应用名称: %s\n", data["app_name"])
			fmt.Printf("版本: %s\n", data["version"])
			fmt.Printf("环境: %s\n", data["env"])
			fmt.Printf("监控品牌: %s\n", data["brand_name"])

			if platforms, ok := data["enabled_platforms"].([]interface{}); ok {
				fmt.Print("已启用平台: ")
				for i, p := range platforms {
					if i > 0 {
						fmt.Print(", ")
					}
					fmt.Print(p)
				}
				fmt.Println()
			}
			fmt.Println("================================")
		}

		// 获取仪表盘统计
		resp2, err := http.Get(apiBaseURL + "/dashboard/stats")
		if err == nil {
			defer resp2.Body.Close()
			body2, _ := io.ReadAll(resp2.Body)
			var result2 map[string]interface{}
			json.Unmarshal(body2, &result2)

			if data, ok := result2["data"].(map[string]interface{}); ok {
				fmt.Println("\n========== 今日概览 ==========")
				fmt.Printf("监测问题总数: %v\n", data["total_questions"])
				fmt.Printf("整体提及率: %v%%\n", data["overall_mention_rate"])
				fmt.Printf("Top1推荐率: %v%%\n", data["overall_top1_rate"])
				fmt.Printf("平均排名: %v\n", data["avg_rank"])
				fmt.Printf("待处理异常: %v\n", data["abnormal_count"])
				fmt.Println("==============================")
			}
		}
	},
}
