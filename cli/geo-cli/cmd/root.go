package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var (
	apiBaseURL string
)

var rootCmd = &cobra.Command{
	Use:   "geo",
	Short: "GEO 智能运营中台 - 命令行工具",
	Long: `GEO (Generative Engine Optimization) 智能运营中台命令行工具
支持监测数据查询、知识库管理、内容管理、竞品分析等操作`,
}

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	rootCmd.PersistentFlags().StringVar(&apiBaseURL, "api", "http://10.17.197.113:8000/api/v1", "后端API地址")
	rootCmd.AddCommand(statusCmd)
	rootCmd.AddCommand(queryCmd)
	rootCmd.AddCommand(scanCmd)
	rootCmd.AddCommand(knowledgeCmd)
	rootCmd.AddCommand(competitorCmd)
}

func checkError(err error) {
	if err != nil {
		fmt.Fprintf(os.Stderr, "错误: %v\n", err)
		os.Exit(1)
	}
}
