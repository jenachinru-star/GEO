package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"

	"github.com/spf13/cobra"
)

var knowledgeCmd = &cobra.Command{
	Use:   "kb",
	Short: "知识库管理",
}

var kbSearchCmd = &cobra.Command{
	Use:   "search [关键词]",
	Short: "语义搜索知识库",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		keyword := args[0]
		fmt.Printf("搜索: %s\n\n", keyword)

		resp, err := http.Post(apiBaseURL+"/knowledge/search?query="+url.QueryEscape(keyword)+"&level=public", "application/json", nil)
		checkError(err)
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		var result map[string]interface{}
		json.Unmarshal(body, &result)

		if items, ok := result["data"].([]interface{}); ok {
			if len(items) == 0 {
				fmt.Println("未找到相关知识")
				return
			}
			fmt.Printf("找到 %d 条相关知识:\n\n", len(items))
			for i, item := range items {
				k := item.(map[string]interface{})
				score := k["score"].(float64) * 100
				fmt.Printf("%d. [%s] (相关度: %.0f%%)\n", i+1, k["title"], score)
				content := k["content"].(string)
				if len(content) > 100 {
					content = content[:100] + "..."
				}
				fmt.Printf("   %s\n\n", content)
			}
		}
	},
}

var kbListCmd = &cobra.Command{
	Use:   "list",
	Short: "列出知识库条目",
	Run: func(cmd *cobra.Command, args []string) {
		resp, err := http.Get(apiBaseURL + "/knowledge?page_size=50")
		checkError(err)
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		var result map[string]interface{}
		json.Unmarshal(body, &result)

		if data, ok := result["data"].(map[string]interface{}); ok {
			if items, ok := data["items"].([]interface{}); ok {
				fmt.Printf("共 %v 条知识:\n\n", data["total"])
				for _, item := range items {
					k := item.(map[string]interface{})
					fmt.Printf("[%s] %s (v%v)\n", k["category"], k["title"], k["version"])
				}
			}
		}
	},
}

func init() {
	knowledgeCmd.AddCommand(kbSearchCmd)
	knowledgeCmd.AddCommand(kbListCmd)
}
