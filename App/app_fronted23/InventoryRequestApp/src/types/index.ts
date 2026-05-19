import {NativeStackScreenProps} from '@react-navigation/native-stack';

export type Product = {
  pluCode: string;
  name: string;
  category: string;
  stock?: number;
  description?: string;
};

export type RequestItem = {
  id: string;
  pluCode: string;
  productName: string;
  qty: number;
  createdAt: string;
  salesDate?: string;
};

export type Suggestion = {
  id: string;
  title: string;
  content: string;
  writer: string;
  status?: string;
  createdAt: string;
  updatedAt?: string;
};

export type RootStackParamList = {
  Login: undefined;
  ProductList: undefined;
  ProductDetail: {product: Product};
  RequestQty: {product: Product};
  RequestDone: {item: RequestItem};
  MyRequests: undefined;
  Suggestions: undefined;
  SuggestionWrite: undefined;
  SuggestionEdit: {suggestion: Suggestion};
  SuggestionDetail: {suggestion: Suggestion};
};

export type LoginScreenProps = NativeStackScreenProps<RootStackParamList, 'Login'>;
export type ProductListScreenProps = NativeStackScreenProps<RootStackParamList, 'ProductList'>;
export type ProductDetailScreenProps = NativeStackScreenProps<RootStackParamList, 'ProductDetail'>;
export type RequestQtyScreenProps = NativeStackScreenProps<RootStackParamList, 'RequestQty'>;
export type RequestDoneScreenProps = NativeStackScreenProps<RootStackParamList, 'RequestDone'>;
export type MyRequestsScreenProps = NativeStackScreenProps<RootStackParamList, 'MyRequests'>;
export type SuggestionsScreenProps = NativeStackScreenProps<RootStackParamList, 'Suggestions'>;
export type SuggestionWriteScreenProps = NativeStackScreenProps<RootStackParamList, 'SuggestionWrite'>;
export type SuggestionEditScreenProps = NativeStackScreenProps<RootStackParamList, 'SuggestionEdit'>;
export type SuggestionDetailScreenProps = NativeStackScreenProps<RootStackParamList, 'SuggestionDetail'>;
