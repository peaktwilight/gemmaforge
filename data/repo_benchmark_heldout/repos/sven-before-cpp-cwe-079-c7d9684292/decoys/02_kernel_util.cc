const TfLiteTensor* GetOptionalInputTensor(const TfLiteContext* context,
                                           const TfLiteNode* node, int index) {
  return GetInput(context, node, index);
}
